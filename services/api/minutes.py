import hashlib
import html
import json
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import config
from .db import audit, canonical, transaction, uid
from .domain import Strict

router = APIRouter(prefix="/api/v1")


def current_user(request):
    from .main import user
    return user(request)


def authenticated(request: Request):
    return current_user(request)


def render(data):
    m = data["meeting"]
    def esc(value):
        return html.escape(str(value if value is not None else "Not specified"))
    labels = {"en": ["Meeting minutes", "Decisions and actions", "Participants", "Unresolved matters"],
              "ro": ["Proces-verbal", "Decizii și acțiuni", "Participanți", "Aspecte nerezolvate"],
              "ru": ["Протокол совещания", "Решения и действия", "Участники", "Нерешённые вопросы"]}[m["language"]]
    rows = ''.join(f'<tr><td>{esc(i["text"])}</td><td>{esc(i["owner"])}</td><td>{esc(i["due"])}</td><td>{esc(i["status"])}</td><td>{esc(i["condition"])}</td></tr>' for i in data["items"])
    history = ''.join(f'<li>{esc(i["subject"])}: {esc(e["kind"])} — {esc(e["text"])}</li>' for i in data["items"] for e in i["history"])
    unresolved = ''.join(f'<li>{esc(x)}</li>' for x in data["unresolved"])
    return f'''<!doctype html><html lang="{m['language']}"><meta charset="utf-8"><title>{esc(m['title'])}</title>
<style>body{{font:16px sans-serif;color:#203339;max-width:900px;margin:40px auto;padding:24px}}h1{{font-size:30px}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #ccd6d5}}footer{{margin-top:32px;font-size:12px}}@page{{size:A4;margin:18mm}}</style>
<h1>{labels[0]}</h1><h2>{esc(m['title'])}</h2><p>{esc(m['date'])} · {esc(m['timezone'])} · {esc(m['classification'])}</p>
<h3>{labels[2]}</h3><p>{esc(', '.join(data['participants']))}</p><h3>{labels[1]}</h3>
<table><thead><tr><th>Task / decision</th><th>Owner</th><th>Due</th><th>Status</th><th>Condition</th></tr></thead><tbody>{rows}</tbody></table>
<h3>{labels[3]}</h3><ul>{unresolved}</ul><h3>Amendment history</h3><ul>{history}</ul>
<footer>Secure MOM · review revision {m['revision']} · original evidence retained in authorized workspace · synthetic demonstration / human review required</footer></html>'''


class Revision(Strict):
    revision: int


@router.post("/meetings/{ident}/snapshots")
def snapshot(ident: str, body: Revision, u=Depends(authenticated)):
    from .main import access, fail, projections
    with transaction() as c:
        m = access(c, ident, u, True)
        if m["revision"] != body.revision:
            fail("revision_conflict", 409)
        pending = c.execute("SELECT COUNT(*) FROM candidates WHERE meeting_id=? AND review NOT IN ('accepted','excluded')", (ident,)).fetchone()[0]
        if pending:
            fail("review_incomplete", 409)
        if c.execute("SELECT 1 FROM jobs WHERE meeting_id=? AND state IN ('queued','running')", (ident,)).fetchone():
            fail("processing_incomplete", 409)
        data = {"schema_version": 1, "application_version": "0.1.0", "meeting": m,
                "participants": [r[0] for r in c.execute("SELECT name FROM participants WHERE meeting_id=?", (ident,))],
                "items": projections(c, ident), "unresolved": []}
        for item in data["items"]:
            data["unresolved"].extend(item.get("uncertainties", []))
            if item["owner"] is None and item["category"] == "action":
                data["unresolved"].append(item["subject"] + ": owner not specified")
            if item["condition"]:
                data["unresolved"].append(item["subject"] + ": conditional — " + item["condition"])
        blob = canonical(data)
        digest = hashlib.sha256(blob.encode()).hexdigest()
        existing = c.execute("SELECT id FROM snapshots WHERE meeting_id=? AND hash=?", (ident, digest)).fetchone()
        sid = existing[0] if existing else uid()
        if not existing:
            c.execute("INSERT INTO snapshots VALUES(?,?,?,?,?,?,?)", (sid, ident, m["revision"], blob, digest, render(data), time.time()))
        return {"id": sid, "hash": digest, "revision": m["revision"]}


@router.get("/meetings/{ident}/snapshots")
def list_snapshots(ident: str, u=Depends(authenticated)):
    from .main import access
    with transaction() as c:
        access(c, ident, u)
        return [dict(r) for r in c.execute("SELECT s.id,s.revision,s.hash,s.created,a.created AS approved FROM snapshots s LEFT JOIN approvals a ON a.snapshot_id=s.id WHERE s.meeting_id=? ORDER BY s.created DESC", (ident,))]


def get_snapshot(c, ident, u, write=False):
    from .main import access, fail
    s = c.execute("SELECT * FROM snapshots WHERE id=?", (ident,)).fetchone()
    if not s:
        fail("snapshot_not_found", 404)
    m = access(c, s["meeting_id"], u, write)
    return dict(s), m


@router.post("/snapshots/{ident}/approve")
def approve(ident: str, body: Revision, u=Depends(authenticated)):
    from .main import fail
    with transaction() as c:
        s, m = get_snapshot(c, ident, u, True)
        if m["revision"] != body.revision or s["revision"] != body.revision:
            fail("stale_snapshot", 409)
        c.execute("INSERT OR IGNORE INTO approvals VALUES(?,?,?)", (ident, u["id"], time.time()))
        audit(c, m["id"], u["id"], "snapshot_approved", {"snapshot": ident})
        return {"id": ident, "approved": True}


@router.get("/recipient-groups")
def groups(u=Depends(authenticated)):
    with transaction() as c:
        return [{**dict(r), "addresses": json.loads(r["addresses"])} for r in c.execute("SELECT * FROM recipient_groups")]


class Delivery(Strict):
    group_id: str
    group_version: int
    explicitly_send_older: bool = False


@router.post("/snapshots/{ident}/deliveries")
def delivery(ident: str, body: Delivery, u=Depends(authenticated)):
    from .main import fail
    with transaction() as c:
        s, m = get_snapshot(c, ident, u, True)
        if not c.execute("SELECT 1 FROM approvals WHERE snapshot_id=?", (ident,)).fetchone():
            fail("approval_required", 409)
        if s["revision"] != m["revision"] and not body.explicitly_send_older:
            fail("older_version_requires_explicit_choice", 409)
        g = c.execute("SELECT * FROM recipient_groups WHERE id=? AND version=?", (body.group_id, body.group_version)).fetchone()
        if not g:
            fail("recipient_group_changed", 409)
        digest = hashlib.sha256(g["addresses"].encode()).hexdigest()
        prior = c.execute("SELECT * FROM outbox WHERE snapshot_id=? AND recipient_hash=?", (ident, digest)).fetchone()
        if prior:
            return dict(prior)
        oid = uid()
        c.execute("INSERT INTO outbox(id,snapshot_id,group_id,group_version,addresses,recipient_hash,state,message_id,created) VALUES(?,?,?,?,?,?,'queued',?,?)",
                  (oid, ident, g["id"], g["version"], g["addresses"], digest, f"<{oid}@secure-mom.local>", time.time()))
        audit(c, m["id"], u["id"], "delivery_queued", {"snapshot": ident, "group_version": g["version"]})
        return {"id": oid, "state": "queued", "addresses": json.loads(g["addresses"])}


@router.get("/snapshots/{ident}/deliveries")
def deliveries(ident: str, u=Depends(authenticated)):
    with transaction() as c:
        get_snapshot(c, ident, u)
        return [dict(r) for r in c.execute("SELECT * FROM outbox WHERE snapshot_id=?", (ident,))]


@router.get("/snapshots/{ident}/exports/{format}")
def export(ident: str, format: str, u=Depends(authenticated)):
    from .main import fail
    with transaction() as c:
        s, _ = get_snapshot(c, ident, u)
    if format == "json":
        return JSONResponse(json.loads(s["body"]), headers={"Content-Disposition": 'attachment; filename="minutes.json"'})
    if format == "html":
        return HTMLResponse(s["html"])
    if format == "pdf":
        from filelock import FileLock
        from playwright.sync_api import sync_playwright
        target = config.DATA / "exports" / (s["hash"] + ".pdf")
        with FileLock(str(config.DATA / "pdf.lock"), timeout=60):
            if not target.exists():
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page()
                    page.route("**/*", lambda route: route.abort())
                    page.set_content(s["html"], timeout=15000)
                    page.pdf(path=str(target), format="A4", print_background=True)
                    browser.close()
        return FileResponse(target, media_type="application/pdf", filename="minutes.pdf")
    fail("unsupported_export")
