import hashlib
import html
import json
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import config
from .brand import NAME as PRODUCT_NAME
from .db import audit, canonical, transaction, uid
from .domain import Strict

router = APIRouter(prefix="/api/v1")


def current_user(request):
    from .main import user

    return user(request)


def authenticated(request: Request):
    return current_user(request)


LABELS = {
    "en": {
        "no_items": "No reviewed decisions or actions.",
        "no_history": "No amendments recorded.",
        "no_unresolved": "No unresolved matters recorded.",
        "no_participants": "No participants entered.",
        "title": "Meeting minutes",
        "items": "Decisions and actions",
        "participants": "Participants",
        "unresolved": "Unresolved matters",
        "task": "Task / decision",
        "owner": "Owner",
        "due": "Due",
        "status": "Status",
        "condition": "Condition",
        "value": "Quantity / value",
        "history": "Amendment history",
        "human": "Secretary amendment",
        "unknown": "Not specified",
        "revision": "Review revision",
        "evidence": "Original evidence retained in the authorized workspace",
        "owner_missing": "owner not specified",
        "conditional": "conditional",
        "audio_flags": "Automated audio flags from the latest analysis: {count}. Review the source recording; these may be false alarms. Transcript edits do not recalculate these flags.",
    },
    "ro": {
        "no_items": "Nu există decizii sau acțiuni verificate.",
        "no_history": "Nu sunt înregistrate modificări.",
        "no_unresolved": "Nu sunt înregistrate aspecte nerezolvate.",
        "no_participants": "Nu sunt introduși participanți.",
        "title": "Proces-verbal",
        "items": "Decizii și acțiuni",
        "participants": "Participanți",
        "unresolved": "Aspecte nerezolvate",
        "task": "Sarcină / decizie",
        "owner": "Responsabil",
        "due": "Termen",
        "status": "Stare",
        "condition": "Condiție",
        "value": "Cantitate / valoare",
        "history": "Istoricul modificărilor",
        "human": "Modificare a secretarului",
        "unknown": "Nespecificat",
        "revision": "Revizia verificării",
        "evidence": "Dovezile originale sunt păstrate în spațiul autorizat",
        "owner_missing": "responsabil nespecificat",
        "conditional": "condiționat",
        "audio_flags": "Semnalări audio automate din ultima analiză: {count}. Verificați înregistrarea sursă; pot fi alarme false. Editarea transcrierii nu recalculează aceste semnalări.",
        "proposed": "propus",
        "confirmed": "confirmat",
        "rejected": "respins",
        "cancelled": "anulat",
        "information": "informație",
        "propose": "propunere",
        "confirm": "confirmare",
        "amend": "modificare",
        "reject": "respingere",
        "cancel": "anulare",
        "reopen": "redeschidere",
        "inform": "informare",
    },
    "ru": {
        "no_items": "Нет проверенных решений или действий.",
        "no_history": "Изменения не зафиксированы.",
        "no_unresolved": "Нерешённые вопросы не зафиксированы.",
        "no_participants": "Участники не указаны.",
        "title": "Протокол совещания",
        "items": "Решения и действия",
        "participants": "Участники",
        "unresolved": "Нерешённые вопросы",
        "task": "Задача / решение",
        "owner": "Ответственный",
        "due": "Срок",
        "status": "Статус",
        "condition": "Условие",
        "value": "Количество / значение",
        "history": "История изменений",
        "human": "Изменение секретаря",
        "unknown": "Не указано",
        "revision": "Редакция проверки",
        "evidence": "Исходные подтверждения сохранены в рабочем пространстве с контролем доступа",
        "owner_missing": "ответственный не указан",
        "conditional": "условно",
        "audio_flags": "Автоматические отметки аудио по последнему анализу: {count}. Проверьте исходную запись; отметки могут быть ложными. Правки расшифровки не пересчитывают эти отметки.",
        "proposed": "предложено",
        "confirmed": "подтверждено",
        "rejected": "отклонено",
        "cancelled": "отменено",
        "information": "сведения",
        "propose": "предложение",
        "confirm": "подтверждение",
        "amend": "изменение",
        "reject": "отклонение",
        "cancel": "отмена",
        "reopen": "возобновление",
        "inform": "информация",
    },
}


def render(data):
    m = data["meeting"]
    labels = LABELS[m["language"]]
    template = data.get("template", {})
    title = template.get("titles", {}).get(m["language"]) or labels["title"]

    def esc(value):
        return html.escape(str(value if value is not None else labels["unknown"]))

    rows = "".join(
        f"<tr><td>{esc(i['text'])}</td><td>{esc(i['owner'])}</td><td>{esc(i['due'])}</td><td>{esc(labels.get(i['status'], i['status']))}</td><td>{esc(i['condition'])}</td><td>{esc(i.get('value'))}</td></tr>"
        for i in data["items"]
    )
    history = "".join(
        f"<li>{esc(i['subject'])}: {esc(labels['human'] if e.get('human_amendment') else labels.get(e['kind'], e['kind']))} — {esc(e['text'])}</li>"
        for i in data["items"]
        for e in i["history"]
    )
    unresolved = "".join(f"<li>{esc(x)}</li>" for x in data["unresolved"])
    headers = "".join(
        f"<th>{esc(labels[k])}</th>" for k in ("task", "owner", "due", "status", "condition", "value")
    )
    table = f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>" if data["items"] else f"<p>{labels['no_items']}</p>"
    history = f"<ul>{history}</ul>" if history else f"<p>{labels['no_history']}</p>"
    unresolved = f"<ul>{unresolved}</ul>" if unresolved else f"<p>{labels['no_unresolved']}</p>"
    return f'''<!doctype html><html lang="{m["language"]}"><meta charset="utf-8"><title>{esc(m["title"])}</title>
<style>*{{box-sizing:border-box}}body{{font:14px/1.5 sans-serif;color:#183438;max-width:900px;margin:32px auto;padding:24px;overflow-wrap:anywhere}}h1{{font-size:28px;line-height:1.2}}h2{{font-size:20px}}h3{{font-size:15px;margin-top:24px;break-after:avoid}}table{{border-collapse:collapse;table-layout:fixed;width:100%;font-size:12px}}td,th{{text-align:left;vertical-align:top;padding:9px 6px;border-bottom:1px solid #ccd6d5;overflow-wrap:anywhere}}th{{background:#edf5f2}}th:first-child{{width:28%}}th:nth-child(2){{width:18%}}th:nth-child(3){{width:12%}}th:nth-child(4){{width:16%}}th:nth-child(5){{width:12%}}th:nth-child(6){{width:14%}}thead{{display:table-header-group}}tr{{break-inside:avoid}}footer{{margin-top:32px;font-size:11px;border-top:2px solid #287f78;padding-top:12px}}@page{{size:A4;margin:18mm;@bottom-right{{content:counter(page);font:10px sans-serif;color:#587074}}}}@media print{{body{{max-width:none;margin:0;padding:0;font-size:12px}}table{{font-size:11px}}a{{color:inherit}}}}</style>
<h1>{esc(title)}</h1><h2>{esc(m["title"])}</h2><p>{esc(m["date"] or labels["unknown"])} · {esc(m["timezone"] or labels["unknown"])} · {esc(m["classification"])}</p>
<p style="white-space:pre-wrap">{esc(template.get("introduction", ""))}</p><h3>{labels["participants"]}</h3><p>{esc(", ".join(data["participants"]) or labels["no_participants"])}</p><h3>{labels["items"]}</h3>
{table}
<h3>{labels["unresolved"]}</h3>{unresolved}<h3>{labels["history"]}</h3>{history}
<footer>{esc(data.get("product_name", PRODUCT_NAME))} · {labels["revision"]} {m["revision"]} · {labels["evidence"]}</footer></html>'''


class Revision(Strict):
    revision: int


@router.post("/meetings/{ident}/snapshots")
def snapshot(ident: str, body: Revision, u=Depends(authenticated)):
    from .main import access, fail, projections
    from .settings import load_template

    with transaction() as c:
        m = access(c, ident, u, True)
        if m["revision"] != body.revision:
            fail("revision_conflict", 409)
        if c.execute("SELECT 1 FROM transcript_analysis_state WHERE meeting_id=?", (ident,)).fetchone():
            fail("transcript_reanalysis_required", 409)
        pending = c.execute(
            "SELECT COUNT(*) FROM candidates WHERE meeting_id=? AND review NOT IN ('accepted','excluded')",
            (ident,),
        ).fetchone()[0]
        if pending:
            fail("review_incomplete", 409)
        if c.execute(
            "SELECT 1 FROM jobs WHERE meeting_id=? AND state IN ('queued','running')", (ident,)
        ).fetchone():
            fail("processing_incomplete", 409)
        data = {
            "schema_version": 1,
            "template_version": 6,
            "product_name": PRODUCT_NAME,
            "template": load_template(c, m["classification"]),
            "application_version": "0.1.0",
            "meeting": m,
            "participants": [
                r[0] for r in c.execute("SELECT name FROM participants WHERE meeting_id=?", (ident,))
            ],
            "items": projections(c, ident),
            "unresolved": [],
        }
        data["audio_checks"] = [dict(row) for row in c.execute(
            "SELECT j.id AS job_id,j.asset_id,a.kind,COUNT(*) AS count FROM audio_checks a JOIN jobs j ON j.id=a.job_id "
            "WHERE j.meeting_id=? AND j.id=(SELECT latest.id FROM jobs latest WHERE latest.asset_id=j.asset_id "
            "AND latest.meeting_id=j.meeting_id AND COALESCE(json_extract(latest.config,'$.transcript_only'),0)=0 "
            "ORDER BY latest.created DESC,latest.rowid DESC LIMIT 1) "
            "AND NOT EXISTS(SELECT 1 FROM transcript_additions t WHERE t.job_id=a.job_id AND t.start=a.start "
            "AND t.end=a.end AND a.kind='speech_without_transcript') "
            "GROUP BY j.id,j.asset_id,a.kind ORDER BY j.id,a.kind", (ident,))]
        flag_count = sum(row["count"] for row in data["audio_checks"])
        if flag_count:
            data["unresolved"].append(LABELS[m["language"]]["audio_flags"].format(count=flag_count))
        for item in data["items"]:
            data["unresolved"].extend(item.get("uncertainties", []))
            if item["owner"] is None and item["category"] == "action":
                data["unresolved"].append(item["subject"] + ": " + LABELS[m["language"]]["owner_missing"])
            if item["condition"]:
                data["unresolved"].append(
                    item["subject"] + ": " + LABELS[m["language"]]["conditional"] + " — " + item["condition"]
                )
        blob = canonical(data)
        digest = hashlib.sha256(blob.encode()).hexdigest()
        existing = c.execute(
            "SELECT id FROM snapshots WHERE meeting_id=? AND hash=?", (ident, digest)
        ).fetchone()
        sid = existing[0] if existing else uid()
        if not existing:
            c.execute(
                "INSERT INTO snapshots VALUES(?,?,?,?,?,?,?)",
                (sid, ident, m["revision"], blob, digest, render(data), time.time()),
            )
        return {"id": sid, "hash": digest, "revision": m["revision"]}


@router.get("/meetings/{ident}/snapshots")
def list_snapshots(ident: str, u=Depends(authenticated)):
    from .main import access

    with transaction() as c:
        access(c, ident, u)
        return [
            dict(r)
            for r in c.execute(
                "SELECT s.id,s.revision,s.hash,s.created,json_extract(s.body,'$.template.recipient_group_id') AS suggested_group_id,json_extract(s.body,'$.template.version') AS template_revision,a.created AS approved FROM snapshots s LEFT JOIN approvals a ON a.snapshot_id=s.id WHERE s.meeting_id=? ORDER BY s.created DESC",
                (ident,),
            )
        ]


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
        if c.execute(
            "SELECT 1 FROM jobs WHERE meeting_id=? AND state IN ('queued','running')", (m["id"],)
        ).fetchone():
            fail("processing_incomplete", 409)
        c.execute("INSERT OR IGNORE INTO approvals VALUES(?,?,?)", (ident, u["id"], time.time()))
        audit(c, m["id"], u["id"], "snapshot_approved", {"snapshot": ident})
        return {"id": ident, "approved": True}


@router.get("/recipient-groups")
def groups(u=Depends(authenticated)):
    with transaction() as c:
        return [
            {**dict(r), "addresses": json.loads(r["addresses"])}
            for r in c.execute("SELECT * FROM recipient_groups")
        ]


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
        g = c.execute(
            "SELECT * FROM recipient_groups WHERE id=? AND version=?", (body.group_id, body.group_version)
        ).fetchone()
        if not g:
            fail("recipient_group_changed", 409)
        digest = hashlib.sha256(g["addresses"].encode()).hexdigest()
        prior = c.execute(
            "SELECT * FROM outbox WHERE snapshot_id=? AND recipient_hash=?", (ident, digest)
        ).fetchone()
        if prior:
            return dict(prior)
        oid = uid()
        c.execute(
            "INSERT INTO outbox(id,snapshot_id,group_id,group_version,addresses,recipient_hash,state,message_id,created) VALUES(?,?,?,?,?,?,'queued',?,?)",
            (
                oid,
                ident,
                g["id"],
                g["version"],
                g["addresses"],
                digest,
                f"<{oid}@secure-mom.local>",
                time.time(),
            ),
        )
        audit(c, m["id"], u["id"], "delivery_queued", {"snapshot": ident, "group_version": g["version"]})
        return {"id": oid, "state": "queued", "addresses": json.loads(g["addresses"])}


@router.get("/snapshots/{ident}/deliveries")
def deliveries(ident: str, u=Depends(authenticated)):
    with transaction() as c:
        get_snapshot(c, ident, u)
        return [dict(r) for r in c.execute("SELECT * FROM outbox WHERE snapshot_id=?", (ident,))]


class RetryDelivery(Strict):
    explicitly_send_older: bool = False


@router.post("/deliveries/{ident}/retry")
def retry_delivery(ident: str, body: RetryDelivery, u=Depends(authenticated)):
    from .main import fail

    with transaction() as c:
        row = c.execute("SELECT * FROM outbox WHERE id=?", (ident,)).fetchone()
        if not row:
            fail("delivery_not_found", 404)
        s, m = get_snapshot(c, row["snapshot_id"], u, True)
        if not c.execute("SELECT 1 FROM approvals WHERE snapshot_id=?", (s["id"],)).fetchone():
            fail("approval_required", 409)
        if s["revision"] != m["revision"] and not body.explicitly_send_older:
            fail("older_version_requires_explicit_choice", 409)
        if row["state"] == "queued":
            return {"id": ident, "state": "queued"}
        if row["state"] != "failed":
            fail("delivery_not_safe_to_retry", 409)
        # A failed attempt never entered send_message. Keep the original recipients,
        # snapshot and Message-ID; uncertain/accepted attempts must never be replayed.
        c.execute("UPDATE outbox SET state='queued',error=NULL WHERE id=?", (ident,))
        audit(c, m["id"], u["id"], "delivery_retry_queued", {"delivery": ident})
        return {"id": ident, "state": "queued"}


@router.get("/snapshots/{ident}/exports/{format}")
def export(ident: str, format: str, u=Depends(authenticated)):
    from .main import fail

    with transaction() as c:
        s, _ = get_snapshot(c, ident, u)
    if format == "json":
        return JSONResponse(
            json.loads(s["body"]), headers={"Content-Disposition": 'attachment; filename="minutes.json"'}
        )
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
