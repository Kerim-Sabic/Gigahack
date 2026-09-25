import asyncio
import hashlib
import json
import os
import secrets
import sqlite3
import time
import wave
from contextlib import asynccontextmanager
from datetime import date as CalendarDate
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from filelock import FileLock, Timeout

from . import config
from .audio import atomic_write, decode, sha
from .db import audit, canonical, migrate, transaction, uid
from .dates import resolve as resolve_date
from .domain import Strict, reduce_events
from .schemas import AudioChecksPage, AccountSummary, AccountView, MeetingDetail, MeetingView, SegmentView
from .provenance import runtime_identity

passwords = PasswordHasher()
attempts = {}


@asynccontextmanager
async def lifespan(app):
    migrate()
    yield


app = FastAPI(title="Secure MOM", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def safety(request, call_next):
    request.state.request_id = uid()
    if request.method in ("POST", "PUT", "PATCH"):
        length = request.headers.get("content-length")
        if length is None or request.headers.get("transfer-encoding"):
            return JSONResponse({"code": "content_length_required"}, 411)
        if not length.isdecimal():
            return JSONResponse({"code": "invalid_content_length"}, 400)
        limit = config.MAX_BYTES + 1024 * 1024 if request.url.path.endswith("/uploads") else 8 * 1024 * 1024
        if int(length) > limit:
            return JSONResponse({"code": "request_too_large"}, 413)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin != config.ORIGIN:
            return JSONResponse({"code": "origin_denied", "request_id": request.state.request_id}, 403)
        if request.cookies.get("mom_session"):
            with transaction() as c:
                s = c.execute(
                    "SELECT csrf FROM sessions WHERE id=?", (request.cookies["mom_session"],)
                ).fetchone()
            if not s or not secrets.compare_digest(s["csrf"], request.headers.get("x-csrf-token", "")):
                return JSONResponse({"code": "csrf_denied", "request_id": request.state.request_id}, 403)
    try:
        response = await call_next(request)
    except Exception:
        # Generic operational logs never include request bodies or transcript search strings.
        print(canonical({"code": "internal_error", "request_id": request.state.request_id}), flush=True)
        response = JSONResponse({"code": "internal_error", "request_id": request.state.request_id}, 500)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(HTTPException)
async def error(request, exc):
    return JSONResponse(
        {"code": str(exc.detail), "message": str(exc.detail), "request_id": request.state.request_id},
        exc.status_code,
    )


@app.exception_handler(sqlite3.IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse({"code": "data_conflict", "request_id": request.state.request_id}, 409)


@app.exception_handler(Exception)
async def internal_error(request, exc):
    return JSONResponse({"code": "internal_error", "request_id": request.state.request_id}, 500)


def fail(code, status=400):
    raise HTTPException(status, code)


def user(request: Request):
    with transaction() as c:
        u = c.execute(
            "SELECT u.*,s.csrf FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.id=? AND s.expires>?",
            (request.cookies.get("mom_session", ""), time.time()),
        ).fetchone()
    if not u:
        fail("authentication_required", 401)
    return dict(u)


def access(c, meeting, u, write=False):
    m = c.execute(
        "SELECT m.* FROM meetings m JOIN members x ON x.meeting_id=m.id WHERE m.id=? AND x.user_id=?",
        (meeting, u["id"]),
    ).fetchone()
    if not m:
        fail("meeting_not_found", 404)
    if write and u["role"] == "viewer":
        fail("read_only", 403)
    return dict(m)


def revision(c, m, expected):
    if m["revision"] != expected:
        fail("revision_conflict", 409)
    c.execute("UPDATE meetings SET revision=revision+1 WHERE id=?", (m["id"],))


class Credentials(Strict):
    name: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=12, max_length=256)


class Account(Credentials):
    role: Literal["admin", "secretary", "viewer"] = "secretary"


def session(c, u, response):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    c.execute("INSERT INTO sessions VALUES(?,?,?,?)", (token, u["id"], time.time() + 8 * 3600, csrf))
    response.set_cookie(
        "mom_session",
        token,
        httponly=True,
        secure=config.ORIGIN.startswith("https:"),
        samesite="strict",
        max_age=28800,
    )
    return {
        "id": u["id"],
        "name": u["name"],
        "role": u["role"],
        "csrf": csrf,
        "language": u.get("language", "en"),
    }


@app.get("/api/v1/setup")
def setup_status():
    with transaction() as c:
        return {"required": not c.execute("SELECT 1 FROM users LIMIT 1").fetchone()}


@app.post("/api/v1/setup", response_model=AccountView)
def setup(body: Credentials, response: Response, request: Request):
    if request.client.host not in ("127.0.0.1", "::1", "testclient"):
        fail("setup_requires_loopback", 403)
    hashed = passwords.hash(body.password)
    with transaction() as c:
        if c.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            fail("setup_already_complete", 409)
        u = {"id": uid(), "name": body.name, "role": "admin"}
        c.execute(
            "INSERT INTO users(id,name,password,role) VALUES(?,?,?,?)", (u["id"], u["name"], hashed, "admin")
        )
        c.execute(
            "INSERT INTO recipient_groups VALUES(?,?,?,?)",
            (uid(), "Local demo", 1, '["secretary@secure-mom.test"]'),
        )
        return session(c, u, response)


@app.post("/api/v1/sessions", response_model=AccountView)
def login(body: Credentials, request: Request, response: Response):
    key = request.client.host
    attempts[key] = [t for t in attempts.get(key, []) if t > time.time() - 60]
    if len(attempts[key]) >= 8:
        fail("login_rate_limit", 429)
    attempts[key].append(time.time())
    with transaction() as c:
        u = c.execute("SELECT * FROM users WHERE name=?", (body.name,)).fetchone()
        try:
            if not u or not passwords.verify(u["password"], body.password):
                fail("invalid_credentials", 401)
        except VerificationError:
            fail("invalid_credentials", 401)
        return session(c, dict(u), response)


@app.delete("/api/v1/sessions/current")
def logout(request: Request, response: Response, u=Depends(user)):
    with transaction() as c:
        c.execute("DELETE FROM sessions WHERE id=?", (request.cookies["mom_session"],))
    response.delete_cookie("mom_session")
    return {"ok": True}


@app.get("/api/v1/me", response_model=AccountView)
def me(u=Depends(user)):
    return {k: u[k] for k in ("id", "name", "role", "language", "csrf")}


class Preference(Strict):
    language: Literal["en", "ro", "ru"]


@app.patch("/api/v1/me")
def preference(body: Preference, u=Depends(user)):
    with transaction() as c:
        c.execute("UPDATE users SET language=? WHERE id=?", (body.language, u["id"]))
    return body


@app.get("/api/v1/accounts", response_model=list[AccountSummary])
def accounts(u=Depends(user)):
    if u["role"] != "admin":
        fail("admin_required", 403)
    with transaction() as c:
        return [dict(r) for r in c.execute("SELECT id,name,role,language FROM users ORDER BY name")]


@app.post("/api/v1/accounts")
def account(body: Account, u=Depends(user)):
    if u["role"] != "admin":
        fail("admin_required", 403)
    with transaction() as c:
        ident = uid()
        c.execute(
            "INSERT INTO users(id,name,password,role) VALUES(?,?,?,?)",
            (ident, body.name, passwords.hash(body.password), body.role),
        )
        return {"id": ident}


class Meeting(Strict):
    title: str = Field(min_length=1, max_length=200)
    date: CalendarDate | None = None
    timezone: str = ""
    language: Literal["en", "ro", "ru"] = "en"
    classification: Literal["Medical", "Executive", "Administrative"] = "Administrative"
    participants: list[str] = Field(default_factory=list, max_length=100)


@app.post("/api/v1/meetings", response_model=MeetingView)
def create_meeting(body: Meeting, request: Request, u=Depends(user)):
    if u["role"] == "viewer":
        fail("read_only", 403)
    try:
        if body.timezone:
            ZoneInfo(body.timezone)
    except (KeyError, ValueError):
        fail("invalid_timezone")
    with transaction() as c:
        key = request.headers.get("idempotency-key")
        digest = hashlib.sha256(canonical(body.model_dump(mode="json")).encode()).hexdigest()
        if key:
            if len(key) > 100:
                fail("invalid_idempotency_key")
            prior = c.execute(
                "SELECT * FROM idempotency WHERE user_id=? AND key=? AND route='create_meeting'",
                (u["id"], key),
            ).fetchone()
            if prior:
                if prior["body_hash"] != digest:
                    fail("idempotency_conflict", 409)
                return json.loads(prior["response"])
        ident = uid()
        c.execute(
            "INSERT INTO meetings(id,title,date,timezone,language,classification,created) VALUES(?,?,?,?,?,?,?)",
            (
                ident,
                body.title,
                (body.date.isoformat() if body.date else ""),
                body.timezone,
                body.language,
                body.classification,
                time.time(),
            ),
        )
        c.execute("INSERT INTO members VALUES(?,?)", (ident, u["id"]))
        for name in body.participants:
            c.execute("INSERT INTO participants VALUES(?,?,?)", (uid(), ident, name[:200]))
        audit(c, ident, u["id"], "meeting_created")
        result = access(c, ident, u)
        if key:
            c.execute(
                "INSERT INTO idempotency VALUES(?,?,'create_meeting',?,?)",
                (u["id"], key, digest, canonical(result)),
            )
        return result


@app.get("/api/v1/meetings", response_model=list[MeetingView])
def meetings(u=Depends(user)):
    with transaction() as c:
        return [
            dict(r)
            for r in c.execute(
                "SELECT m.* FROM meetings m JOIN members x ON x.meeting_id=m.id WHERE x.user_id=? ORDER BY created DESC",
                (u["id"],),
            )
        ]


@app.get("/api/v1/meetings/{ident}", response_model=MeetingDetail)
def meeting(ident: str, u=Depends(user)):
    with transaction() as c:
        m = access(c, ident, u)
        for table in ("participants", "assets", "jobs", "recordings"):
            m[table] = [dict(r) for r in c.execute(f"SELECT * FROM {table} WHERE meeting_id=?", (ident,))]
        for a in m["assets"]:
            a.pop("path")
        for r in m["recordings"]:
            stats = c.execute(
                "SELECT COUNT(*),COALESCE(SUM(samples),0),MAX(sequence) FROM chunks WHERE recording_id=?",
                (r["id"],),
            ).fetchone()
            r["acknowledged_chunks"], r["acknowledged_samples"], r["last_sequence"] = tuple(stats)
    from .progress import read_progress

    for job in m["jobs"]:
        job["progress"] = read_progress(config.DATA, job)
    return m


class MeetingEdit(Meeting):
    revision: int


@app.patch("/api/v1/meetings/{ident}")
def update_meeting(ident: str, body: MeetingEdit, u=Depends(user)):
    try:
        if body.timezone:
            ZoneInfo(body.timezone)
    except (KeyError, ValueError):
        fail("invalid_timezone")
    with transaction() as c:
        m = access(c, ident, u, True)
        if c.execute(
            "SELECT 1 FROM jobs WHERE meeting_id=? AND state IN ('queued','running')", (ident,)
        ).fetchone():
            fail("cancel_processing_before_metadata_edit", 409)
        revision(c, m, body.revision)
        c.execute(
            "UPDATE meetings SET title=?,date=?,timezone=?,language=?,classification=? WHERE id=?",
            (body.title, (body.date.isoformat() if body.date else ""), body.timezone, body.language, body.classification, ident),
        )
        if (body.date.isoformat() if body.date else "") != m["date"] or body.timezone != m["timezone"]:
            c.execute(
                "UPDATE candidates SET review='needs_review' WHERE meeting_id=? AND review!='excluded'",
                (ident,),
            )
        c.execute("DELETE FROM participants WHERE meeting_id=?", (ident,))
        for name in body.participants:
            c.execute("INSERT INTO participants VALUES(?,?,?)", (uid(), ident, name[:200]))
        audit(c, ident, u["id"], "metadata_updated")
        return access(c, ident, u)


class DeleteMeeting(Strict):
    revision: int
    confirm_title: str


@app.delete("/api/v1/meetings/{ident}")
def delete_meeting(ident: str, body: DeleteMeeting, u=Depends(user)):
    import shutil
    from uuid import UUID

    try:
        UUID(ident)
    except ValueError:
        fail("invalid_meeting_id")
    if u["role"] != "admin":
        fail("member_admin_required", 403)
    source = (config.DATA / "audio" / ident).resolve()
    expected_parent = (config.DATA / "audio").resolve()
    if source.parent != expected_parent:
        fail("storage_boundary_error", 500)
    trash_parent = (config.DATA / "deleted").resolve()
    trash_parent.mkdir(parents=True, exist_ok=True)
    trash = trash_parent / ident
    moved = False
    exports = []
    jobs = []
    try:
        with transaction() as c:
            m = access(c, ident, u, True)
            if m["revision"] != body.revision or m["title"] != body.confirm_title:
                fail("deletion_confirmation_conflict", 409)
            if c.execute(
                "SELECT 1 FROM jobs WHERE meeting_id=? AND state IN ('queued','running')", (ident,)
            ).fetchone():
                fail("cancel_processing_before_deletion", 409)
            exports = [r[0] for r in c.execute("SELECT hash FROM snapshots WHERE meeting_id=?", (ident,))]
            jobs = [r[0] for r in c.execute("SELECT id FROM jobs WHERE meeting_id=?", (ident,))]
            if source.exists():
                source.rename(trash)
                moved = True
            c.execute(
                "DELETE FROM outbox WHERE snapshot_id IN (SELECT id FROM snapshots WHERE meeting_id=?)",
                (ident,),
            )
            c.execute(
                "DELETE FROM approvals WHERE snapshot_id IN (SELECT id FROM snapshots WHERE meeting_id=?)",
                (ident,),
            )
            c.execute(
                "DELETE FROM segment_history WHERE segment_id IN (SELECT id FROM segments WHERE meeting_id=?)",
                (ident,),
            )
            c.execute(
                "DELETE FROM chunks WHERE recording_id IN (SELECT id FROM recordings WHERE meeting_id=?)",
                (ident,),
            )
            for table in (
                "evidence",
                "accepted_events",
                "candidates",
                "segments",
                "jobs",
                "snapshots",
                "recordings",
                "assets",
                "participants",
                "members",
                "audit",
            ):
                c.execute(f"DELETE FROM {table} WHERE meeting_id=?", (ident,))
            c.execute("DELETE FROM meetings WHERE id=?", (ident,))
            audit(
                c,
                ident,
                u["id"],
                "meeting_deleted",
                {"backups": "operator retention policy applies separately"},
            )
    except BaseException:
        if moved and trash.exists():
            trash.rename(source)
        raise
    try:
        if trash.exists() and trash.resolve().parent == trash_parent:
            shutil.rmtree(trash)
        for job in jobs:
            folder = (config.DATA / "jobs" / job).resolve()
            if folder.parent != (config.DATA / "jobs").resolve():
                raise OSError("job cleanup boundary mismatch")
            if folder.exists():
                shutil.rmtree(folder)
        for digest in exports:
            path = (config.DATA / "exports" / (digest + ".pdf")).resolve()
            if path.parent == (config.DATA / "exports").resolve():
                path.unlink(missing_ok=True)
    except OSError:
        with transaction() as c:
            audit(c, ident, u["id"], "deletion_file_cleanup_pending")
        return {"deleted": True, "file_cleanup": "pending_operator_action"}
    return {
        "deleted": True,
        "file_cleanup": "complete",
        "backups": "not deleted; apply backup retention separately",
    }


class Grant(Strict):
    user_id: str


@app.post("/api/v1/meetings/{ident}/members")
def grant(ident: str, body: Grant, u=Depends(user)):
    with transaction() as c:
        access(c, ident, u, True)
        if u["role"] != "admin":
            fail("member_admin_required", 403)
        if not c.execute("SELECT 1 FROM users WHERE id=?", (body.user_id,)).fetchone():
            fail("account_not_found", 404)
        c.execute("INSERT OR IGNORE INTO members VALUES(?,?)", (ident, body.user_id))
        audit(c, ident, u["id"], "member_granted", {"user": body.user_id})
        return {"ok": True}


@app.post("/api/v1/meetings/{ident}/uploads")
def upload(ident: str, file: UploadFile, u=Depends(user)):
    with transaction() as c:
        access(c, ident, u, True)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"):
        fail("unsupported_audio_type")
    asset = uid()
    folder = config.DATA / "audio" / ident / asset
    folder.mkdir(parents=True)
    original = folder / ("original" + ext)
    size = 0
    with original.open("wb") as f:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > config.MAX_BYTES:
                f.close()
                original.unlink()
                fail("upload_too_large", 413)
            f.write(chunk)
        f.flush()
        import os

        os.fsync(f.fileno())
    target = folder / "source.wav"
    try:
        metadata = decode(original, target)
    except Exception:
        fail("audio_decode_failed")
    with transaction() as c:
        access(c, ident, u, True)
        c.execute(
            "INSERT INTO assets VALUES(?,?,?,?,?,?,?,?)",
            (
                asset,
                ident,
                str(target),
                sha(original),
                metadata["sample_rate"],
                metadata["samples"],
                1,
                canonical({**json.loads(metadata["original"]), "file": original.name}),
            ),
        )
    return {"id": asset, "samples": metadata["samples"], "sample_rate": 16000}


class Capture(Strict):
    sample_rate: int = Field(ge=8000, le=96000)


@app.post("/api/v1/meetings/{ident}/recordings")
def recording(ident: str, body: Capture, u=Depends(user)):
    with transaction() as c:
        access(c, ident, u, True)
        rid = uid()
        c.execute("INSERT INTO recordings(id,meeting_id,rate) VALUES(?,?,?)", (rid, ident, body.sample_rate))
        return {"id": rid}


@app.put("/api/v1/recordings/{ident}/chunks/{sequence}")
async def chunk(ident: str, sequence: int, request: Request, u=Depends(user)):
    if sequence < 0 or sequence > 3600:
        fail("invalid_sequence")
    content = bytearray()
    async for part in request.stream():
        content.extend(part)
        if len(content) > 384000:
            fail("chunk_too_large", 413)
    if not content or len(content) % 2:
        fail("invalid_pcm")
    digest = hashlib.sha256(content).hexdigest()
    with transaction() as c:
        r = c.execute("SELECT * FROM recordings WHERE id=?", (ident,)).fetchone()
        if not r:
            fail("recording_not_found", 404)
        access(c, r["meeting_id"], u, True)
        prior = c.execute(
            "SELECT * FROM chunks WHERE recording_id=? AND sequence=?", (ident, sequence)
        ).fetchone()
        if prior and prior["hash"] != digest:
            fail("chunk_content_conflict", 409)
        if r["state"] != "recording":
            fail("recording_sealed", 409)
        if not prior:
            path = config.DATA / "audio" / r["meeting_id"] / ident / f"{sequence}.pcm"
            atomic_write(path, content)
            c.execute(
                "INSERT INTO chunks VALUES(?,?,?,?,?)",
                (ident, sequence, digest, len(content) // 2, str(path)),
            )
        saved = c.execute("SELECT SUM(samples) FROM chunks WHERE recording_id=?", (ident,)).fetchone()[0]
        return {"sequence": sequence, "hash": digest, "acknowledged_samples": saved, "sample_rate": r["rate"]}


class Finish(Strict):
    count: int = Field(ge=1, le=3601)
    gaps: list[dict] = Field(default_factory=list, max_length=1000)


@app.post("/api/v1/recordings/{ident}/finish")
def finish(ident: str, body: Finish, u=Depends(user)):
    # Authorize before constructing the app-owned recording lock path.
    with transaction() as c:
        row = c.execute("SELECT * FROM recordings WHERE id=?", (ident,)).fetchone()
        if not row:
            fail("recording_not_found", 404)
        access(c, row["meeting_id"], u, True)
        folder = config.DATA / "audio" / row["meeting_id"] / row["id"]
    folder.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(folder / "finalize.lock"))
    try:
        lock.acquire(timeout=0)
    except Timeout:
        fail("recording_finalizing", 409)
    try:
        with transaction() as c:
            r = c.execute("SELECT * FROM recordings WHERE id=?", (ident,)).fetchone()
            if not r:
                fail("recording_not_found", 404)
            access(c, r["meeting_id"], u, True)
            chunks = c.execute("SELECT * FROM chunks WHERE recording_id=? ORDER BY sequence", (ident,)).fetchall()
            if len(chunks) != body.count or any(ch["sequence"] != i for i, ch in enumerate(chunks)):
                fail("missing_chunks", 409)
            if r["state"] == "sealed":
                if r["gaps"] != canonical(body.gaps):
                    fail("recording_sealed", 409)
                asset = c.execute("SELECT * FROM assets WHERE id=?", (ident,)).fetchone()
                if not asset:
                    fail("recording_asset_missing", 409)
                return {"id": ident, "samples": asset["samples"], "sample_rate": asset["sample_rate"]}
            if r["state"] not in ("recording", "finalizing"):
                fail("recording_sealed", 409)
            # OS lock serializes retries, including recovery after a process died in finalizing.
            c.execute("UPDATE recordings SET state='finalizing' WHERE id=?", (ident,))
        try:
            path = folder / "original.wav"
            temporary = folder / "original.partial.wav"
            with temporary.open("w+b") as stream:
                with wave.open(stream, "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(r["rate"])
                    for ch in chunks:
                        pcm = Path(ch["path"]).read_bytes()
                        if hashlib.sha256(pcm).hexdigest() != ch["hash"]:
                            fail("recording_chunk_corrupt", 409)
                        w.writeframes(pcm)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            target = folder / "source.wav"
            metadata = decode(path, target)
            original_hash = sha(path)
            with transaction() as c:
                access(c, r["meeting_id"], u, True)
                c.execute(
                    "INSERT INTO assets VALUES(?,?,?,?,?,?,?,?)",
                    (ident, r["meeting_id"], str(target), original_hash, 16000,
                     metadata["samples"], 1, canonical({"rate": r["rate"], "gaps": body.gaps})),
                )
                c.execute("UPDATE recordings SET state='sealed',gaps=? WHERE id=?", (canonical(body.gaps), ident))
            return {"id": ident, "samples": metadata["samples"], "sample_rate": 16000}
        except BaseException:
            with transaction() as c:
                c.execute("UPDATE recordings SET state='recording' WHERE id=? AND state='finalizing'", (ident,))
            raise
    finally:
        lock.release()


class Queue(Strict):
    asset_id: str
    device: Literal["cuda", "cpu"] = "cuda"
    parakeet: bool = False
    diarization: bool = False


@app.post("/api/v1/meetings/{ident}/jobs")
def queue(ident: str, body: Queue, u=Depends(user)):
    from .capabilities import capabilities

    from services.worker.settings import load_settings

    inference_settings = load_settings().model_dump()
    available = capabilities(inference_settings)
    for name in ("parakeet", "diarization"):
        if getattr(body, name) and not available[name]["available"]:
            fail(name + "_not_prepared", 409)
    with transaction() as c:
        meeting_context = access(c, ident, u, True)
        if not c.execute(
            "SELECT 1 FROM assets WHERE id=? AND meeting_id=?", (body.asset_id, ident)
        ).fetchone():
            fail("asset_not_found", 404)
        prompt_hash = hashlib.sha256((config.ROOT / "services/worker/stage.py").read_bytes()).hexdigest()
        model_manifest = config.ROOT / "manifests/models.lock.json"
        source_versions = [
            tuple(r)
            for r in c.execute(
                "SELECT id,revision FROM segments WHERE asset_id=? ORDER BY start,id", (body.asset_id,)
            )
        ]
        glossary = c.execute("SELECT version,body FROM settings WHERE key='glossary'").fetchone()
        settings = canonical(
            {
                "device": body.device,
                "inference": inference_settings,
                "parakeet": body.parakeet,
                "diarization": body.diarization,
                "prompt_hash": prompt_hash,
                "implementation": runtime_identity(),
                "contract": 1,
                "source_versions": source_versions,
                "glossary": json.loads(glossary["body"]) if glossary else [],
                "glossary_version": glossary["version"] if glossary else 0,
                "meeting_context": {
                    key: meeting_context[key] for key in ("date", "timezone", "language", "classification")
                },
                "models_hash": hashlib.sha256(model_manifest.read_bytes()).hexdigest()
                if model_manifest.exists()
                else None,
            }
        )
        old = c.execute(
            "SELECT * FROM jobs WHERE meeting_id=? AND asset_id=? AND config=?",
            (ident, body.asset_id, settings),
        ).fetchone()
        if old:
            return dict(old)
        job = uid()
        c.execute(
            "INSERT INTO jobs(id,meeting_id,asset_id,state,stage,config,created) VALUES(?,?,?,'queued','queued',?,?)",
            (job, ident, body.asset_id, settings, time.time()),
        )
        c.execute("UPDATE meetings SET status='queued' WHERE id=?", (ident,))
        return {"id": job, "state": "queued"}


@app.get("/api/v1/jobs/{ident}/audio-checks", response_model=AudioChecksPage)
def audio_checks(ident: str, offset: int = 0, limit: int = 50, u=Depends(user)):
    with transaction() as c:
        job = c.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
        if not job:
            fail("job_not_found", 404)
        access(c, job["meeting_id"], u)
        rows = c.execute("SELECT kind,start,end FROM audio_checks WHERE job_id=? ORDER BY start,end,kind LIMIT ? OFFSET ?",
                         (ident, min(max(limit, 1), 100), max(offset, 0))).fetchall()
        total = c.execute("SELECT COUNT(*) FROM audio_checks WHERE job_id=?", (ident,)).fetchone()[0]
        return {"asset_id": job["asset_id"], "total": total, "items": [dict(r) for r in rows],
                "scope": "Automated observations from this processing attempt; not proof of missing speech or transcript accuracy"}


@app.post("/api/v1/jobs/{ident}/{action}")
def job_action(ident: str, action: Literal["cancel", "retry"], u=Depends(user)):
    with transaction() as c:
        j = c.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
        if not j:
            fail("job_not_found", 404)
        access(c, j["meeting_id"], u, True)
        if action == "cancel":
            c.execute("UPDATE jobs SET cancel=1 WHERE id=?", (ident,))
        else:
            if j["state"] not in ("failed", "cancelled"):
                fail("job_not_retryable", 409)
            c.execute("UPDATE jobs SET state='queued',cancel=0,error=NULL WHERE id=?", (ident,))
        return {"ok": True}


@app.get("/api/v1/meetings/{ident}/transcript", response_model=list[SegmentView])
def transcript(ident: str, q: str = "", offset: int = 0, limit: int = 100, u=Depends(user)):
    with transaction() as c:
        access(c, ident, u)
        rows = c.execute(
            "SELECT * FROM segments WHERE meeting_id=? AND instr(lower(text),lower(?))>0 ORDER BY start LIMIT ? OFFSET ?",
            (ident, q[:200], min(max(limit, 1), 200), max(offset, 0)),
        ).fetchall()
        return [dict(r) for r in rows]


class Edit(Strict):
    revision: int
    text: str = Field(min_length=1, max_length=10000)
    speaker: str | None = Field(default=None, max_length=200)


@app.get("/api/v1/segments/{ident}", response_model=SegmentView)
def get_segment(ident: str, u=Depends(user)):
    with transaction() as c:
        s = c.execute("SELECT * FROM segments WHERE id=?", (ident,)).fetchone()
        if not s:
            fail("segment_not_found", 404)
        access(c, s["meeting_id"], u)
        return dict(s)


@app.get("/api/v1/segments/{ident}/history")
def segment_history(ident: str, u=Depends(user)):
    with transaction() as c:
        s = c.execute("SELECT * FROM segments WHERE id=?", (ident,)).fetchone()
        if not s:
            fail("segment_not_found", 404)
        access(c, s["meeting_id"], u)
        return [
            dict(r)
            for r in c.execute(
                "SELECT revision,text,actor,created FROM segment_history WHERE segment_id=? ORDER BY revision",
                (ident,),
            )
        ]


@app.post("/api/v1/segments/{ident}/revisions")
def edit_segment(ident: str, body: Edit, u=Depends(user)):
    with transaction() as c:
        s = c.execute("SELECT * FROM segments WHERE id=?", (ident,)).fetchone()
        if not s:
            fail("segment_not_found", 404)
        access(c, s["meeting_id"], u, True)
        if s["revision"] != body.revision:
            fail("revision_conflict", 409)
        c.execute(
            "INSERT INTO segment_history VALUES(?,?,?,?,?,?)",
            (uid(), ident, s["revision"], s["text"], u["id"], time.time()),
        )
        c.execute(
            "UPDATE segments SET revision=revision+1,text=?,speaker=? WHERE id=?",
            (body.text, body.speaker, ident),
        )
        c.execute(
            "UPDATE candidates SET review='needs_review' WHERE review!='excluded' AND id IN (SELECT candidate_id FROM evidence WHERE segment_id=?)",
            (ident,),
        )
        c.execute(
            "UPDATE meetings SET revision=revision+1,status='awaiting_review' WHERE id=?", (s["meeting_id"],)
        )
        audit(c, s["meeting_id"], u["id"], "transcript_corrected", {"segment": ident})
        return {"revision": s["revision"] + 1}


def projections(c, ident):
    rows = c.execute(
        "SELECT e.* FROM accepted_events e JOIN candidates x ON x.id=e.candidate_id WHERE e.meeting_id=? AND x.review='accepted'",
        (ident,),
    ).fetchall()
    return reduce_events([dict(r) for r in rows])


@app.get("/api/v1/meetings/{ident}/items")
def items(ident: str, u=Depends(user)):
    with transaction() as c:
        m = access(c, ident, u)
        candidates = [
            dict(r)
            for r in c.execute("SELECT * FROM candidates WHERE meeting_id=? ORDER BY source_order", (ident,))
        ]
        for row in candidates:
            row["body"] = json.loads(row["body"])
            row["evidence"] = [
                dict(e) for e in c.execute("SELECT * FROM evidence WHERE candidate_id=?", (row["id"],))
            ]
        return {"revision": m["revision"], "candidates": candidates, "items": projections(c, ident)}


class Review(Strict):
    revision: int
    action: Literal["accepted", "excluded"]


class Correction(Strict):
    revision: int
    subject: str | None = Field(default=None, min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=2000)
    owner: str | None = Field(default=None, max_length=200)
    due: CalendarDate | None = None
    condition: str | None = Field(default=None, max_length=2000)
    value: str | None = Field(default=None, max_length=200)
    resolved_issues: list[str] = Field(default_factory=list, max_length=30)
    reason: str = Field(min_length=3, max_length=1000)
    category: Literal["action", "decision", "information"] | None = None
    kind: Literal["propose", "confirm", "amend", "reject", "cancel", "reopen", "inform"] | None = None


@app.post("/api/v1/items/{ident}/corrections")
def correct_item(ident: str, body: Correction, u=Depends(user)):
    with transaction() as c:
        old = c.execute("SELECT * FROM candidates WHERE id=?", (ident,)).fetchone()
        if not old:
            fail("candidate_not_found", 404)
        m = access(c, old["meeting_id"], u, True)
        revision(c, m, body.revision)
        e = json.loads(old["body"])
        if (
            e.get("raw_due")
            and resolve_date(e["raw_due"], m["date"]) != e.get("due")
            and (str(body.due) if body.due else None) == e.get("due")
        ):
            fail("meeting_date_requires_reextraction", 409)
        changed = [
            f
            for f in ("text", "owner", "due")
            if e.get(f) != (str(body.due) if f == "due" and body.due else getattr(body, f))
        ]
        if body.subject is not None:
            body.subject = body.subject.strip()
            if not body.subject:
                fail("invalid_subject")
        for field in ("category", "kind", "subject"):
            if getattr(body, field) is not None and getattr(body, field) != e[field]:
                changed.append(field)
        for field in ("condition", "value"):
            if field in body.model_fields_set and getattr(body, field) != e.get(field):
                changed.append(field)
        if any(issue not in e["uncertainties"] for issue in body.resolved_issues):
            fail("unknown_review_issue")
        if body.resolved_issues:
            changed.append("uncertainties")
        if not changed:
            fail("no_changes")
        new = {
            **e,
            "text": body.text,
            "owner": body.owner,
            "due": str(body.due) if body.due else None,
            "changed_fields": changed,
            "evidence": [x for x in e["evidence"] if x["field"] not in changed],
            "human_amendment": {
                "previous_candidate": ident,
                "previous_subject": e["subject"],
                "actor": u["id"],
                "reason": body.reason,
                "fields": changed,
                "created": time.time(),
            },
            "uncertainties": [x for x in e["uncertainties"] if x not in body.resolved_issues],
        }
        if "due" in changed:
            new["raw_due"] = None
        if "value" in changed:
            # Human replacement has its own provenance; never retain old machine quantity evidence.
            new["quantity"] = None
        elif "subject" in changed and new.get("quantity"):
            new["quantity"] = {**new["quantity"], "scope": body.subject}
        for field in ("condition", "value"):
            if field in body.model_fields_set:
                new[field] = getattr(body, field)
        new["human_amendment"]["resolved_issues"] = body.resolved_issues
        for field in ("category", "kind", "subject"):
            value = getattr(body, field)
            if value is not None and value != e[field]:
                new[field] = value
        if new.get("value") and any("critical" in issue.lower() for issue in new["uncertainties"]):
            fail("critical_value_unresolved", 409)
        new_id = uid()
        retained = c.execute(
            "SELECT e.*,s.revision AS current_revision FROM evidence e JOIN segments s ON s.id=e.segment_id WHERE e.candidate_id=?",
            (ident,),
        ).fetchall()
        retained = [r for r in retained if r["field"] not in changed]
        if any(r["revision"] != r["current_revision"] for r in retained):
            fail("stale_evidence_requires_reextraction", 409)
        c.execute("UPDATE candidates SET review='excluded' WHERE id=?", (ident,))
        c.execute(
            "INSERT INTO candidates(id,meeting_id,subject,body,review,source_order,actor,created) VALUES(?,?,?,?,'accepted',?,?,?)",
            (new_id, m["id"], new["subject"], canonical(new), old["source_order"], u["id"], time.time()),
        )
        for ref in retained:
            c.execute(
                "INSERT INTO evidence SELECT ?,meeting_id,?,segment_id,revision,field,quote,start,end FROM evidence WHERE id=?",
                (uid(), new_id, ref["id"]),
            )
        c.execute(
            "INSERT INTO accepted_events VALUES(?,?,?,?,?,?,?)",
            (uid(), m["id"], new_id, canonical(new), old["source_order"], u["id"], time.time()),
        )
        audit(
            c,
            m["id"],
            u["id"],
            "secretary_amendment",
            {"previous": ident, "replacement": new_id, "fields": changed},
        )
        return {"id": new_id, "revision": m["revision"] + 1}


@app.get("/api/v1/items/{ident}/history")
def item_history(ident: str, u=Depends(user)):
    with transaction() as c:
        row = c.execute("SELECT * FROM candidates WHERE id=?", (ident,)).fetchone()
        if not row:
            fail("candidate_not_found", 404)
        access(c, row["meeting_id"], u)
        rows = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM candidates WHERE meeting_id=? ORDER BY created", (row["meeting_id"],)
            )
        ]
        included = {r["id"] for r in rows if r["subject"] == row["subject"]}
        edges = [
            json.loads(r["payload"])
            for r in c.execute(
                "SELECT payload FROM audit WHERE meeting_id=? AND kind='secretary_amendment'",
                (row["meeting_id"],),
            )
        ]
        # Retain amendment ancestors/descendants even when a reviewer linked topics.
        while True:
            before = len(included)
            for edge in edges:
                pair = {edge["previous"], edge["replacement"]}
                if pair & included:
                    included.update(pair)
            if len(included) == before:
                break
        return [r for r in rows if r["id"] in included]


@app.post("/api/v1/review-issues/{ident}/resolve")
def review(ident: str, body: Review, u=Depends(user)):
    with transaction() as c:
        event = c.execute("SELECT * FROM candidates WHERE id=?", (ident,)).fetchone()
        if not event:
            fail("candidate_not_found", 404)
        m = access(c, event["meeting_id"], u, True)
        revision(c, m, body.revision)
        if body.action == "accepted":
            stale = c.execute(
                "SELECT 1 FROM evidence e JOIN segments s ON s.id=e.segment_id WHERE e.candidate_id=? AND e.revision<>s.revision",
                (ident,),
            ).fetchone()
            if stale:
                fail("stale_evidence_requires_reextraction", 409)
            e = json.loads(event["body"])
            if e.get("raw_due") and resolve_date(e["raw_due"], m["date"]) != e.get("due"):
                fail("meeting_date_requires_reextraction", 409)
            if any("critical" in issue.lower() for issue in e["uncertainties"]) and e.get("value"):
                fail("critical_value_unresolved", 409)
            c.execute(
                "INSERT INTO accepted_events VALUES(?,?,?,?,?,?,?)",
                (uid(), m["id"], ident, event["body"], event["source_order"], u["id"], time.time()),
            )
        c.execute("UPDATE candidates SET review=?,actor=? WHERE id=?", (body.action, u["id"], ident))
        audit(c, m["id"], u["id"], "review_" + body.action, {"candidate": ident})
        return {"revision": m["revision"] + 1}


@app.get("/api/v1/assets/{ident}/audio")
def audio(ident: str, u=Depends(user)):
    with transaction() as c:
        a = c.execute("SELECT * FROM assets WHERE id=?", (ident,)).fetchone()
        if not a:
            fail("asset_not_found", 404)
        access(c, a["meeting_id"], u)
        return FileResponse(a["path"], media_type="audio/wav")


@app.get("/api/v1/evidence/{ident}/audio")
def evidence_audio(ident: str, u=Depends(user)):
    with transaction() as c:
        e = c.execute(
            "SELECT e.*,s.asset_id FROM evidence e JOIN segments s ON s.id=e.segment_id WHERE e.id=?",
            (ident,),
        ).fetchone()
        if not e:
            fail("evidence_not_found", 404)
        access(c, e["meeting_id"], u)
        a = c.execute("SELECT * FROM assets WHERE id=?", (e["asset_id"],)).fetchone()
        return FileResponse(a["path"], media_type="audio/wav")


@app.get("/api/v1/meetings/{ident}/stream")
async def stream(ident: str, request: Request, u=Depends(user)):
    with transaction() as c:
        access(c, ident, u)

    async def events():
        while not await request.is_disconnected():
            with transaction() as c:
                if not c.execute(
                    "SELECT 1 FROM sessions WHERE id=? AND expires>?",
                    (request.cookies.get("mom_session", ""), time.time()),
                ).fetchone():
                    return
                # Headers are already sent. Revocation ends the stream instead of
                # raising an HTTP error after a successful response has started.
                if not c.execute(
                    "SELECT 1 FROM members WHERE meeting_id=? AND user_id=?",
                    (ident, u["id"]),
                ).fetchone():
                    return
                state = [
                    dict(r) for r in c.execute("SELECT id,state,stage FROM jobs WHERE meeting_id=?", (ident,))
                ]
            yield "data: " + canonical(state) + "\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/v1/actions")
def actions(u=Depends(user)):
    with transaction() as c:
        result = []
        for m in c.execute("SELECT meeting_id FROM members WHERE user_id=?", (u["id"],)).fetchall():
            result.extend(
                {**i, "meeting_id": m[0]} for i in projections(c, m[0]) if i["category"] == "action"
            )
        return result


@app.get("/api/v1/system/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/system/proof")
def proof(u=Depends(user)):
    from .capabilities import capabilities

    return {
        "inference": "local only",
        "network_observation": "Not measured",
        "target_laptop": "NOT RUN — TARGET MACHINE REQUIRED",
        "models": {n: (config.MODELS / n).exists() for n in ("whisper", "qwen")},
        "translation_review": "Romanian and Russian need native review",
        "capabilities": capabilities(),
    }


from .minutes import router as minutes_router  # noqa: E402

app.include_router(minutes_router)
from .settings import router as settings_router  # noqa: E402

app.include_router(settings_router)
web = config.ROOT / "apps/web/dist"
if web.exists():
    app.mount("/", StaticFiles(directory=web, html=True), name="web")
