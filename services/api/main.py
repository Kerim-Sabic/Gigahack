import asyncio
import hashlib
import json
import secrets
import time
import wave
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from . import config
from .audio import atomic_write, decode, sha
from .db import audit, canonical, migrate, transaction, uid
from .domain import Strict, reduce_events

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
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin != config.ORIGIN:
            return JSONResponse({"code": "origin_denied", "request_id": request.state.request_id}, 403)
        if request.cookies.get("mom_session"):
            with transaction() as c:
                s = c.execute("SELECT csrf FROM sessions WHERE id=?", (request.cookies["mom_session"],)).fetchone()
            if not s or not secrets.compare_digest(s["csrf"], request.headers.get("x-csrf-token", "")):
                return JSONResponse({"code": "csrf_denied", "request_id": request.state.request_id}, 403)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(HTTPException)
async def error(request, exc):
    return JSONResponse({"code": str(exc.detail), "message": str(exc.detail),
                         "request_id": request.state.request_id}, exc.status_code)


def fail(code, status=400):
    raise HTTPException(status, code)


def user(request: Request):
    with transaction() as c:
        u = c.execute("SELECT u.*,s.csrf FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.id=? AND s.expires>?",
                      (request.cookies.get("mom_session", ""), time.time())).fetchone()
    if not u:
        fail("authentication_required", 401)
    return dict(u)


def access(c, meeting, u, write=False):
    m = c.execute("SELECT m.* FROM meetings m JOIN members x ON x.meeting_id=m.id WHERE m.id=? AND x.user_id=?",
                  (meeting, u["id"])).fetchone()
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
    response.set_cookie("mom_session", token, httponly=True, secure=config.ORIGIN.startswith("https:"),
                        samesite="strict", max_age=28800)
    return {"id": u["id"], "name": u["name"], "role": u["role"], "csrf": csrf,
            "language": u.get("language", "en")}


@app.get("/api/v1/setup")
def setup_status():
    with transaction() as c:
        return {"required": not c.execute("SELECT 1 FROM users LIMIT 1").fetchone()}


@app.post("/api/v1/setup")
def setup(body: Credentials, response: Response, request: Request):
    if request.client.host not in ("127.0.0.1", "::1", "testclient"):
        fail("setup_requires_loopback", 403)
    hashed = passwords.hash(body.password)
    with transaction() as c:
        if c.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            fail("setup_already_complete", 409)
        u = {"id": uid(), "name": body.name, "role": "admin"}
        c.execute("INSERT INTO users(id,name,password,role) VALUES(?,?,?,?)", (u["id"], u["name"], hashed, "admin"))
        c.execute("INSERT INTO recipient_groups VALUES(?,?,?,?)", (uid(), "Local demo", 1, '["secretary@secure-mom.test"]'))
        return session(c, u, response)


@app.post("/api/v1/sessions")
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


@app.get("/api/v1/me")
def me(u=Depends(user)):
    return {k: u[k] for k in ("id", "name", "role", "language", "csrf")}


class Preference(Strict):
    language: Literal["en", "ro", "ru"]


@app.patch("/api/v1/me")
def preference(body: Preference, u=Depends(user)):
    with transaction() as c:
        c.execute("UPDATE users SET language=? WHERE id=?", (body.language, u["id"]))
    return body


@app.post("/api/v1/accounts")
def account(body: Account, u=Depends(user)):
    if u["role"] != "admin":
        fail("admin_required", 403)
    with transaction() as c:
        ident = uid()
        c.execute("INSERT INTO users(id,name,password,role) VALUES(?,?,?,?)",
                  (ident, body.name, passwords.hash(body.password), body.role))
        return {"id": ident}


class Meeting(Strict):
    title: str = Field(min_length=1, max_length=200)
    date: date
    timezone: str = "Europe/Chisinau"
    language: Literal["en", "ro", "ru"] = "en"
    classification: Literal["Medical", "Executive", "Administrative"] = "Administrative"
    participants: list[str] = Field(default_factory=list, max_length=100)


@app.post("/api/v1/meetings")
def create_meeting(body: Meeting, u=Depends(user)):
    if u["role"] == "viewer":
        fail("read_only", 403)
    try:
        ZoneInfo(body.timezone)
    except (KeyError, ValueError):
        fail("invalid_timezone")
    with transaction() as c:
        ident = uid()
        c.execute("INSERT INTO meetings(id,title,date,timezone,language,classification,created) VALUES(?,?,?,?,?,?,?)",
                  (ident, body.title, str(body.date), body.timezone, body.language, body.classification, time.time()))
        c.execute("INSERT INTO members VALUES(?,?)", (ident, u["id"]))
        for name in body.participants:
            c.execute("INSERT INTO participants VALUES(?,?,?)", (uid(), ident, name[:200]))
        audit(c, ident, u["id"], "meeting_created")
        return access(c, ident, u)


@app.get("/api/v1/meetings")
def meetings(u=Depends(user)):
    with transaction() as c:
        return [dict(r) for r in c.execute("SELECT m.* FROM meetings m JOIN members x ON x.meeting_id=m.id WHERE x.user_id=? ORDER BY created DESC", (u["id"],))]


@app.get("/api/v1/meetings/{ident}")
def meeting(ident: str, u=Depends(user)):
    with transaction() as c:
        m = access(c, ident, u)
        for table in ("participants", "assets", "jobs"):
            m[table] = [dict(r) for r in c.execute(f"SELECT * FROM {table} WHERE meeting_id=?", (ident,))]
        for a in m["assets"]:
            a.pop("path")
        return m


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
        c.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?)", (asset, ident, str(target), sha(original),
            metadata["sample_rate"], metadata["samples"], 1, canonical({**json.loads(metadata["original"]), "file": original.name})))
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
        prior = c.execute("SELECT * FROM chunks WHERE recording_id=? AND sequence=?", (ident, sequence)).fetchone()
        if prior and prior["hash"] != digest:
            fail("chunk_content_conflict", 409)
        if r["state"] != "recording":
            fail("recording_sealed", 409)
        if not prior:
            path = config.DATA / "audio" / r["meeting_id"] / ident / f"{sequence}.pcm"
            atomic_write(path, content)
            c.execute("INSERT INTO chunks VALUES(?,?,?,?,?)", (ident, sequence, digest, len(content)//2, str(path)))
        saved = c.execute("SELECT SUM(samples) FROM chunks WHERE recording_id=?", (ident,)).fetchone()[0]
        return {"sequence": sequence, "hash": digest, "acknowledged_samples": saved, "sample_rate": r["rate"]}


class Finish(Strict):
    count: int = Field(ge=1, le=3601)
    gaps: list[dict] = Field(default_factory=list, max_length=1000)


@app.post("/api/v1/recordings/{ident}/finish")
def finish(ident: str, body: Finish, u=Depends(user)):
    with transaction() as c:
        r = c.execute("SELECT * FROM recordings WHERE id=?", (ident,)).fetchone()
        if not r:
            fail("recording_not_found", 404)
        access(c, r["meeting_id"], u, True)
        chunks = c.execute("SELECT * FROM chunks WHERE recording_id=? ORDER BY sequence", (ident,)).fetchall()
        if [x["sequence"] for x in chunks] != list(range(body.count)):
            fail("missing_chunks", 409)
        if r["state"] != "recording":
            fail("recording_sealed", 409)
        path = config.DATA / "audio" / r["meeting_id"] / ident / "original.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(r["rate"])
            for ch in chunks:
                w.writeframes(Path(ch["path"]).read_bytes())
        target = path.with_name("source.wav")
        metadata = decode(path, target)
        c.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?)", (ident, r["meeting_id"], str(target), sha(path),
                  16000, metadata["samples"], 1, canonical({"rate": r["rate"], "gaps": body.gaps})))
        c.execute("UPDATE recordings SET state='sealed',gaps=? WHERE id=?", (canonical(body.gaps), ident))
        return {"id": ident, "samples": metadata["samples"], "sample_rate": 16000}


class Queue(Strict):
    asset_id: str
    device: Literal["cuda", "cpu"] = "cuda"


@app.post("/api/v1/meetings/{ident}/jobs")
def queue(ident: str, body: Queue, u=Depends(user)):
    with transaction() as c:
        access(c, ident, u, True)
        if not c.execute("SELECT 1 FROM assets WHERE id=? AND meeting_id=?", (body.asset_id, ident)).fetchone():
            fail("asset_not_found", 404)
        settings = canonical({"device": body.device, "prompt_version": "1", "contract": 1})
        old = c.execute("SELECT * FROM jobs WHERE meeting_id=? AND asset_id=? AND config=?", (ident, body.asset_id, settings)).fetchone()
        if old:
            return dict(old)
        job = uid()
        c.execute("INSERT INTO jobs(id,meeting_id,asset_id,state,stage,config,created) VALUES(?,?,?,'queued','queued',?,?)",
                  (job, ident, body.asset_id, settings, time.time()))
        c.execute("UPDATE meetings SET status='queued' WHERE id=?", (ident,))
        return {"id": job, "state": "queued"}


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


@app.get("/api/v1/meetings/{ident}/transcript")
def transcript(ident: str, q: str = "", offset: int = 0, limit: int = 100, u=Depends(user)):
    with transaction() as c:
        access(c, ident, u)
        rows = c.execute("SELECT * FROM segments WHERE meeting_id=? AND instr(lower(text),lower(?))>0 ORDER BY start LIMIT ? OFFSET ?",
                          (ident, q[:200], min(max(limit, 1), 200), max(offset, 0))).fetchall()
        return [dict(r) for r in rows]


class Edit(Strict):
    revision: int
    text: str = Field(min_length=1, max_length=10000)
    speaker: str | None = Field(default=None, max_length=200)


@app.post("/api/v1/segments/{ident}/revisions")
def edit_segment(ident: str, body: Edit, u=Depends(user)):
    with transaction() as c:
        s = c.execute("SELECT * FROM segments WHERE id=?", (ident,)).fetchone()
        if not s:
            fail("segment_not_found", 404)
        access(c, s["meeting_id"], u, True)
        if s["revision"] != body.revision:
            fail("revision_conflict", 409)
        c.execute("INSERT INTO segment_history VALUES(?,?,?,?,?,?)", (uid(), ident, s["revision"], s["text"], u["id"], time.time()))
        c.execute("UPDATE segments SET revision=revision+1,text=?,speaker=? WHERE id=?", (body.text, body.speaker, ident))
        c.execute("UPDATE candidates SET review='needs_review' WHERE id IN (SELECT candidate_id FROM evidence WHERE segment_id=?)", (ident,))
        c.execute("UPDATE meetings SET revision=revision+1,status='awaiting_review' WHERE id=?", (s["meeting_id"],))
        audit(c, s["meeting_id"], u["id"], "transcript_corrected", {"segment": ident})
        return {"revision": s["revision"] + 1}


def projections(c, ident):
    rows = c.execute("SELECT e.* FROM accepted_events e JOIN candidates x ON x.id=e.candidate_id WHERE e.meeting_id=? AND x.review='accepted'", (ident,)).fetchall()
    return reduce_events([dict(r) for r in rows])


@app.get("/api/v1/meetings/{ident}/items")
def items(ident: str, u=Depends(user)):
    with transaction() as c:
        m = access(c, ident, u)
        candidates = [dict(r) for r in c.execute("SELECT * FROM candidates WHERE meeting_id=? ORDER BY source_order", (ident,))]
        for row in candidates:
            row["body"] = json.loads(row["body"])
            row["evidence"] = [dict(e) for e in c.execute("SELECT * FROM evidence WHERE candidate_id=?", (row["id"],))]
        return {"revision": m["revision"], "candidates": candidates, "items": projections(c, ident)}


class Review(Strict):
    revision: int
    action: Literal["accepted", "excluded"]


@app.post("/api/v1/review-issues/{ident}/resolve")
def review(ident: str, body: Review, u=Depends(user)):
    with transaction() as c:
        event = c.execute("SELECT * FROM candidates WHERE id=?", (ident,)).fetchone()
        if not event:
            fail("candidate_not_found", 404)
        m = access(c, event["meeting_id"], u, True)
        revision(c, m, body.revision)
        if body.action == "accepted":
            stale = c.execute("SELECT 1 FROM evidence e JOIN segments s ON s.id=e.segment_id WHERE e.candidate_id=? AND e.revision<>s.revision", (ident,)).fetchone()
            if stale:
                fail("stale_evidence_requires_reextraction", 409)
            e = json.loads(event["body"])
            if any("critical" in issue.lower() for issue in e["uncertainties"]) and e.get("value"):
                fail("critical_value_unresolved", 409)
            c.execute("INSERT INTO accepted_events VALUES(?,?,?,?,?,?,?)", (uid(), m["id"], ident, event["body"], event["source_order"], u["id"], time.time()))
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
        e = c.execute("SELECT e.*,s.asset_id FROM evidence e JOIN segments s ON s.id=e.segment_id WHERE e.id=?", (ident,)).fetchone()
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
                access(c, ident, u)
                state = [dict(r) for r in c.execute("SELECT id,state,stage FROM jobs WHERE meeting_id=?", (ident,))]
            yield "data: " + canonical(state) + "\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/v1/actions")
def actions(u=Depends(user)):
    with transaction() as c:
        result = []
        for m in c.execute("SELECT meeting_id FROM members WHERE user_id=?", (u["id"],)).fetchall():
            result.extend({**i, "meeting_id": m[0]} for i in projections(c, m[0]) if i["category"] == "action")
        return result


@app.get("/api/v1/system/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/system/proof")
def proof(u=Depends(user)):
    return {"inference": "local only", "network_observation": "Not measured",
            "target_laptop": "NOT RUN — TARGET MACHINE REQUIRED",
            "models": {n: (config.MODELS / n).exists() for n in ("whisper", "qwen")},
            "translation_review": "Romanian and Russian need native review"}


from .minutes import router as minutes_router  # noqa: E402

app.include_router(minutes_router)
web = config.ROOT / "apps/web/dist"
if web.exists():
    app.mount("/", StaticFiles(directory=web, html=True), name="web")

