import io
import json
import time
import wave

import pytest
from fastapi.testclient import TestClient

from services.api import config
from services.api.db import canonical, transaction, uid
from services.api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    with TestClient(app) as c:
        r = c.post("/api/v1/setup", json={"name": "secretary", "password": "synthetic-password-123"})
        assert r.status_code == 200, r.text
        c.headers["x-csrf-token"] = r.json()["csrf"]
        yield c


def new_meeting(c):
    r = c.post(
        "/api/v1/meetings",
        json={"title": "Synthetic maintenance", "date": "2026-09-25", "participants": ["Elena", "Andrei"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_queue_freezes_effective_developer_model_settings(client, monkeypatch):
    from services.worker import settings

    meeting = new_meeting(client)
    asset = client.post(f"/api/v1/meetings/{meeting['id']}/uploads", files={"file": ("synthetic.wav", audio(), "audio/wav")}).json()["id"]
    first = client.post(f"/api/v1/meetings/{meeting['id']}/jobs", json={"asset_id": asset})
    assert first.status_code == 200
    original = settings.load_settings()
    changed = original.model_dump()
    changed["llm"]["context_tokens"] = 8192
    monkeypatch.setattr(settings, "load_settings", lambda: settings.InferenceSettings.model_validate(changed))
    second = client.post(f"/api/v1/meetings/{meeting['id']}/jobs", json={"asset_id": asset})
    assert second.status_code == 200 and second.json()["id"] != first.json()["id"]
    with transaction() as c:
        rows = {r["id"]: json.loads(r["config"])["inference"] for r in c.execute("SELECT id,config FROM jobs")}
    assert rows[first.json()["id"]]["llm"]["context_tokens"] == 4096
    assert rows[second.json()["id"]]["llm"]["context_tokens"] == 8192


def test_unknown_meeting_metadata_is_preserved_without_current_date_defaults(client):
    response = client.post("/api/v1/meetings", json={"title": "Unknown metadata", "date": None, "timezone": ""})
    assert response.status_code == 200
    meeting = response.json()
    assert meeting["date"] == meeting["timezone"] == ""
    updated = client.patch(f"/api/v1/meetings/{meeting['id']}", json={"title": meeting["title"], "revision": meeting["revision"], "date": "2027-01-02", "timezone": "Europe/Chisinau"})
    assert updated.status_code == 200
    restored = client.patch(f"/api/v1/meetings/{meeting['id']}", json={"title": meeting["title"], "revision": updated.json()["revision"], "date": None, "timezone": ""})
    assert restored.status_code == 200 and restored.json()["date"] == ""


def audio():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 32000)
    return stream.getvalue()


def seed_candidate(c, m):
    """Explicit test setup only; no production fixture selector."""
    r = c.post(f"/api/v1/meetings/{m['id']}/uploads", files={"file": ("synthetic.wav", audio(), "audio/wav")})
    assert r.status_code == 200, r.text
    asset = r.json()["id"]
    sid, cid = uid(), uid()
    text = "Elena sends the report. Confirmed."
    event = dict(
        subject="report",
        category="action",
        kind="confirm",
        text="Send report",
        owner="Elena",
        due=None,
        raw_due=None,
        condition=None,
        value=None,
        changed_fields=[],
        uncertainties=[],
        evidence=[
            dict(segment_id=sid, revision=1, field="owner", quote="Elena"),
            dict(segment_id=sid, revision=1, field="text", quote=text),
        ],
    )
    with transaction() as db:
        db.execute(
            "INSERT INTO segments(id,meeting_id,asset_id,revision,start,end,text,raw) VALUES(?,?,?,1,0,32000,?,?)",
            (sid, m["id"], asset, text, text),
        )
        db.execute(
            "INSERT INTO candidates(id,meeting_id,subject,body,source_order,created) VALUES(?,?,?,?,0,?)",
            (cid, m["id"], "report", canonical(event), time.time()),
        )
        db.execute(
            "INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)",
            (uid(), m["id"], cid, sid, 1, "owner", "Elena", 0, 5),
        )
        db.execute(
            "INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)",
            (uid(), m["id"], cid, sid, 1, "text", text, 0, len(text)),
        )
    return sid, cid, asset


def test_review_snapshot_approval_delivery_and_staleness(client):
    m = new_meeting(client)
    sid, cid, _ = seed_candidate(client, m)
    base = f"/api/v1/meetings/{m['id']}"
    assert client.post(base + "/snapshots", json={"revision": 1}).status_code == 409
    r = client.post(f"/api/v1/review-issues/{cid}/resolve", json={"revision": 1, "action": "accepted"})
    assert r.status_code == 200, r.text
    snap = client.post(base + "/snapshots", json={"revision": 2}).json()["id"]
    group = client.get("/api/v1/recipient-groups").json()[0]
    body = {"group_id": group["id"], "group_version": group["version"]}
    assert client.post(f"/api/v1/snapshots/{snap}/deliveries", json=body).status_code == 409
    assert client.post(f"/api/v1/snapshots/{snap}/approve", json={"revision": 2}).status_code == 200
    sent = client.post(f"/api/v1/snapshots/{snap}/deliveries", json=body)
    assert sent.status_code == 200, sent.text
    duplicate = client.post(f"/api/v1/snapshots/{snap}/deliveries", json=body)
    assert duplicate.json()["id"] == sent.json()["id"]
    assert client.get(f"/api/v1/snapshots/{snap}/exports/json").json()["items"][0]["owner"] == "Elena"
    assert (
        client.post(
            f"/api/v1/segments/{sid}/revisions", json={"revision": 1, "text": "Andrei sends the report."}
        ).status_code
        == 200
    )
    assert client.get(base + "/items").json()["items"] == []
    assert client.post(f"/api/v1/snapshots/{snap}/approve", json={"revision": 2}).status_code == 409
    assert client.post(f"/api/v1/snapshots/{snap}/deliveries", json=body).status_code == 409
    assert client.get(f"/api/v1/snapshots/{snap}/exports/json").json()["items"][0]["owner"] == "Elena"


def test_admin_has_no_implicit_content_access(client):
    m = new_meeting(client)
    _, _, asset = seed_candidate(client, m)
    client.post(
        "/api/v1/accounts",
        json={"name": "another-admin", "password": "another-password-123", "role": "admin"},
    )
    client.delete("/api/v1/sessions/current")
    client.headers.pop("x-csrf-token")
    r = client.post("/api/v1/sessions", json={"name": "another-admin", "password": "another-password-123"})
    client.headers["x-csrf-token"] = r.json()["csrf"]
    for route in [
        f"meetings/{m['id']}",
        f"meetings/{m['id']}/transcript",
        f"meetings/{m['id']}/items",
        f"assets/{asset}/audio",
    ]:
        assert client.get("/api/v1/" + route).status_code == 404
    assert client.get("/api/v1/meetings").json() == []


def test_chunk_ack_idempotency_and_gap_rejection(client):
    m = new_meeting(client)
    rid = client.post(f"/api/v1/meetings/{m['id']}/recordings", json={"sample_rate": 16000}).json()["id"]
    url = f"/api/v1/recordings/{rid}/chunks/0"
    r = client.put(url, content=b"\x00\x00" * 32000)
    assert r.status_code == 200, r.text
    assert r.json()["acknowledged_samples"] == 32000
    assert client.put(url, content=b"\x00\x00" * 32000).json() == r.json()
    assert client.put(url, content=b"\x01\x00" * 32000).status_code == 409
    assert client.post(f"/api/v1/recordings/{rid}/finish", json={"count": 2}).status_code == 409
    assert client.post(f"/api/v1/recordings/{rid}/finish", json={"count": 1, "gaps": []}).status_code == 200


def test_csrf_and_origin(client):
    assert (
        client.post("/api/v1/meetings", json={}, headers={"origin": "https://attacker.test"}).status_code
        == 403
    )
    client.headers.pop("x-csrf-token")
    assert client.post("/api/v1/meetings", json={}).status_code == 403


def test_unbounded_or_malformed_request_lengths_are_rejected(client):
    assert client.post("/api/v1/meetings", content=iter([b"{}"])).status_code == 411
    assert (
        client.post("/api/v1/meetings", content=b"{}", headers={"content-length": "invalid"}).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/meetings", content=b"{}", headers={"content-length": str(9 * 1024**2)}
        ).status_code
        == 413
    )


def test_creation_idempotency_detects_changed_payload(client):
    body = {"title": "Synthetic", "date": "2026-09-25"}
    headers = {"idempotency-key": "synthetic-create-1"}
    first = client.post("/api/v1/meetings", json=body, headers=headers)
    second = client.post("/api/v1/meetings", json=body, headers=headers)
    assert first.json()["id"] == second.json()["id"]
    assert (
        client.post("/api/v1/meetings", json={**body, "title": "Different"}, headers=headers).status_code
        == 409
    )


def test_restart_preserves_state(client):
    m = new_meeting(client)
    from services.api.db import migrate

    migrate()
    assert client.get(f"/api/v1/meetings/{m['id']}").json()["title"] == m["title"]


def test_secretary_amendment_has_no_invented_field_evidence(client):
    m = new_meeting(client)
    sid, cid, _ = seed_candidate(client, m)
    r = client.post(
        f"/api/v1/items/{cid}/corrections",
        json={
            "revision": 1,
            "text": "Send report",
            "owner": "Andrei",
            "due": None,
            "reason": "Reviewer correction",
        },
    )
    assert r.status_code == 200, r.text
    data = client.get(f"/api/v1/meetings/{m['id']}/items").json()
    corrected = next(x for x in data["candidates"] if x["id"] == r.json()["id"])
    assert corrected["body"]["human_amendment"]["fields"] == ["owner"]
    assert not any(e["field"] == "owner" for e in corrected["body"]["evidence"])
    assert len(client.get(f"/api/v1/items/{cid}/history").json()) == 2
    assert data["items"][0]["owner"] == "Andrei"
    corrected_id = r.json()["id"]
    with transaction() as c:
        refs = c.execute("SELECT field FROM evidence WHERE candidate_id=?", (corrected_id,)).fetchall()
        assert [x["field"] for x in refs] == ["text"]
    assert (
        client.post(
            f"/api/v1/segments/{sid}/revisions",
            json={"revision": 1, "text": "We withdrew the report.", "speaker": None},
        ).status_code
        == 200
    )
    data = client.get(f"/api/v1/meetings/{m['id']}/items").json()
    assert data["items"] == []
    assert next(x for x in data["candidates"] if x["id"] == corrected_id)["review"] == "needs_review"
    stale = client.post(
        f"/api/v1/items/{corrected_id}/corrections",
        json={
            "revision": 3,
            "text": "Send report",
            "owner": "Elena",
            "due": None,
            "reason": "Stale source must prevent acceptance",
        },
    )
    assert stale.status_code == 409


def test_adversarial_spec_inventory():
    from pathlib import Path

    cases = json.loads(Path("tests/fixtures/adversarial.json").read_text(encoding="utf-8"))
    assert [c["id"] for c in cases] == [f"T{i:02}" for i in range(1, 31)]
    assert all(c["expected"] for c in cases)


def test_manual_topic_link_keeps_original_history_and_exclusion(client):
    m = new_meeting(client)
    sid, cid, _ = seed_candidate(client, m)
    result = client.post(
        f"/api/v1/items/{cid}/corrections",
        json={
            "revision": 1,
            "subject": "maintenance report",
            "text": "Send report",
            "owner": "Elena",
            "reason": "Reviewer links the report to the same maintenance item",
        },
    )
    assert result.status_code == 200, result.text
    linked = result.json()["id"]
    data = client.get(f"/api/v1/meetings/{m['id']}/items").json()
    assert data["items"][0]["subject"] == "maintenance report"
    history = client.get(f"/api/v1/items/{linked}/history").json()
    assert {r["id"] for r in history} == {cid, linked}
    original = next(r for r in history if r["id"] == cid)
    assert original["review"] == "excluded" and original["subject"] == "report"
    amendment = json.loads(next(r for r in history if r["id"] == linked)["body"])["human_amendment"]
    assert amendment["previous_candidate"] == cid and amendment["fields"] == ["subject"]
    client.post(
        f"/api/v1/segments/{sid}/revisions",
        json={"revision": 1, "text": "Elena sends a different report.", "speaker": None},
    )
    history = client.get(f"/api/v1/items/{linked}/history").json()
    assert next(r for r in history if r["id"] == cid)["review"] == "excluded"
    assert next(r for r in history if r["id"] == linked)["review"] == "needs_review"


def test_unrelated_manual_edit_cannot_bypass_critical_quantity_review(client):
    m = new_meeting(client)
    _, cid, _ = seed_candidate(client, m)
    with transaction() as c:
        event = json.loads(c.execute("SELECT body FROM candidates WHERE id=?", (cid,)).fetchone()[0])
        event.update(value="5 mg", uncertainties=["Critical quantity ambiguous"])
        c.execute("UPDATE candidates SET body=? WHERE id=?", (canonical(event), cid))
    result = client.post(
        f"/api/v1/items/{cid}/corrections",
        json={"revision": 1, "text": "Send report", "owner": "Andrei", "reason": "Change only the owner"},
    )
    assert result.status_code == 409 and result.json()["code"] == "critical_value_unresolved"


def test_metadata_edit_invalidates_job_context_and_old_relative_date(client):
    m = new_meeting(client)
    _, cid, asset = seed_candidate(client, m)
    route = f"/api/v1/meetings/{m['id']}"
    job = client.post(route + "/jobs", json={"asset_id": asset}).json()
    edit = {"title": m["title"], "date": "2026-09-26", "revision": 1}
    assert client.patch(route, json=edit).json()["code"] == "cancel_processing_before_metadata_edit"
    with transaction() as c:
        c.execute("UPDATE jobs SET state='complete' WHERE id=?", (job["id"],))
        body = json.loads(c.execute("SELECT body FROM candidates WHERE id=?", (cid,)).fetchone()[0])
        body.update(raw_due="tomorrow", due="2026-09-26")
        c.execute("UPDATE candidates SET body=? WHERE id=?", (canonical(body), cid))
    assert client.patch(route, json=edit).status_code == 200
    assert (
        client.post(
            f"/api/v1/review-issues/{cid}/resolve", json={"revision": 2, "action": "accepted"}
        ).json()["code"]
        == "meeting_date_requires_reextraction"
    )
    next_job = client.post(route + "/jobs", json={"asset_id": asset}).json()
    assert next_job["id"] != job["id"]
    with transaction() as c:
        config_body = json.loads(
            c.execute("SELECT config FROM jobs WHERE id=?", (next_job["id"],)).fetchone()[0]
        )
        assert config_body["meeting_context"]["date"] == "2026-09-26"


def test_account_directory_and_explicit_membership(client):
    m = new_meeting(client)
    created = client.post(
        "/api/v1/accounts", json={"name": "viewer", "password": "synthetic-viewer-password", "role": "viewer"}
    ).json()
    directory = client.get("/api/v1/accounts")
    assert directory.status_code == 200
    assert all(set(row) == {"id", "name", "role", "language"} for row in directory.json())
    assert client.post(f"/api/v1/meetings/{m['id']}/members", json={"user_id": "missing"}).status_code == 404
    assert (
        client.post(f"/api/v1/meetings/{m['id']}/members", json={"user_id": created["id"]}).status_code == 200
    )
    client.delete("/api/v1/sessions/current")
    login = client.post(
        "/api/v1/sessions", json={"name": "viewer", "password": "synthetic-viewer-password"}
    ).json()
    client.headers["x-csrf-token"] = login["csrf"]
    assert client.get("/api/v1/accounts").status_code == 403
    assert client.get(f"/api/v1/meetings/{m['id']}").status_code == 200
    assert (
        client.post(f"/api/v1/meetings/{m['id']}/members", json={"user_id": created["id"]}).status_code == 403
    )


def test_reviewed_quantity_and_condition_are_explicit_human_additions(client):
    m = new_meeting(client)
    _, cid, _ = seed_candidate(client, m)
    issue = "critical quantity ambiguous"
    with transaction() as c:
        original = json.loads(c.execute("SELECT body FROM candidates WHERE id=?", (cid,)).fetchone()[0])
        original["uncertainties"] = [issue]
        c.execute("UPDATE candidates SET body=? WHERE id=?", (canonical(original), cid))
    r = client.post(
        f"/api/v1/items/{cid}/corrections",
        json={
            "revision": 1,
            "text": "Send report",
            "owner": "Elena",
            "due": None,
            "value": "25 beds",
            "condition": "If procurement approves",
            "resolved_issues": [issue],
            "reason": "Synthetic reviewer verified the intended resource quantity",
        },
    )
    assert r.status_code == 200, r.text
    with transaction() as c:
        corrected = json.loads(
            c.execute("SELECT body FROM candidates WHERE id=?", (r.json()["id"],)).fetchone()[0]
        )
        assert corrected["value"] == "25 beds" and corrected["condition"] == "If procurement approves"
        assert corrected["uncertainties"] == []
        assert corrected["human_amendment"]["resolved_issues"] == [issue]
        assert not any(e["field"] in ("value", "condition") for e in corrected["evidence"])
        assert (
            issue
            in json.loads(c.execute("SELECT body FROM candidates WHERE id=?", (cid,)).fetchone()[0])[
                "uncertainties"
            ]
        )


def test_selected_recipient_group_is_versioned_and_addresses_are_frozen(client):
    m = new_meeting(client)
    _, cid, _ = seed_candidate(client, m)
    client.post(f"/api/v1/review-issues/{cid}/resolve", json={"revision": 1, "action": "accepted"})
    sid = client.post(f"/api/v1/meetings/{m['id']}/snapshots", json={"revision": 2}).json()["id"]
    client.post(f"/api/v1/snapshots/{sid}/approve", json={"revision": 2})
    group = client.post(
        "/api/v1/recipient-groups",
        json={"name": "Synthetic chosen recipients", "addresses": ["selected@secure-mom.test"]},
    ).json()
    changed = client.post(
        "/api/v1/recipient-groups",
        json={
            "id": group["id"],
            "version": group["version"],
            "name": group["name"],
            "addresses": ["updated@secure-mom.test"],
        },
    ).json()
    route = f"/api/v1/snapshots/{sid}/deliveries"
    assert (
        client.post(route, json={"group_id": group["id"], "group_version": group["version"]}).status_code
        == 409
    )
    sent = client.post(route, json={"group_id": changed["id"], "group_version": changed["version"]})
    assert sent.status_code == 200
    assert sent.json()["addresses"] == ["updated@secure-mom.test"]


def test_confirmed_retention_deletion_keeps_only_tombstone(client):
    m = new_meeting(client)
    seed_candidate(client, m)
    r = client.request(
        "DELETE", f"/api/v1/meetings/{m['id']}", json={"revision": 1, "confirm_title": "wrong"}
    )
    assert r.status_code == 409
    r = client.request(
        "DELETE", f"/api/v1/meetings/{m['id']}", json={"revision": 1, "confirm_title": m["title"]}
    )
    assert r.status_code == 200, r.text
    assert client.get(f"/api/v1/meetings/{m['id']}").status_code == 404
    with transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM segments").fetchone()[0] == 0
        assert (
            c.execute("SELECT kind FROM audit WHERE meeting_id=?", (m["id"],)).fetchone()[0]
            == "meeting_deleted"
        )


def test_failed_mail_retry_preserves_envelope_and_refuses_uncertainty(client):
    m = new_meeting(client)
    _, cid, _ = seed_candidate(client, m)
    client.post(f"/api/v1/review-issues/{cid}/resolve", json={"revision": 1, "action": "accepted"})
    sid = client.post(f"/api/v1/meetings/{m['id']}/snapshots", json={"revision": 2}).json()["id"]
    client.post(f"/api/v1/snapshots/{sid}/approve", json={"revision": 2})
    group = client.get("/api/v1/recipient-groups").json()[0]
    oid = client.post(
        f"/api/v1/snapshots/{sid}/deliveries",
        json={"group_id": group["id"], "group_version": group["version"]},
    ).json()["id"]
    with transaction() as c:
        prior = dict(c.execute("SELECT * FROM outbox WHERE id=?", (oid,)).fetchone())
        c.execute(
            "UPDATE outbox SET state='failed',error='smtp_transport_error',attempt=1 WHERE id=?", (oid,)
        )
        c.execute("UPDATE meetings SET revision=3 WHERE id=?", (m["id"],))
    route = f"/api/v1/deliveries/{oid}/retry"
    assert client.post(route, json={}).status_code == 409
    assert client.post(route, json={"explicitly_send_older": True}).status_code == 200
    assert client.post(route, json={"explicitly_send_older": True}).status_code == 200
    with transaction() as c:
        after = dict(c.execute("SELECT * FROM outbox WHERE id=?", (oid,)).fetchone())
        assert after["state"] == "queued" and after["attempt"] == 1
        assert all(after[k] == prior[k] for k in ("message_id", "addresses", "snapshot_id", "recipient_hash"))
        c.execute("UPDATE outbox SET state='uncertain' WHERE id=?", (oid,))
    assert (
        client.post(route, json={"explicitly_send_older": True}).json()["code"]
        == "delivery_not_safe_to_retry"
    )


def test_migration_upgrade_keeps_existing_accounts(tmp_path, monkeypatch):
    import sqlite3
    from services.api.db import migrate, MIGRATIONS

    monkeypatch.setattr(config, "DATA", tmp_path)
    with sqlite3.connect(tmp_path / "app.sqlite") as c:
        c.executescript((MIGRATIONS / "001_initial.sql").read_text())
        c.execute("INSERT INTO users VALUES('u','existing','hash','secretary','en')")
    migrate()
    with transaction() as c:
        assert c.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 2
        assert c.execute("SELECT name FROM users").fetchone()[0] == "existing"


def test_private_surfaces_and_range_require_membership(client):
    m = new_meeting(client)
    sid, cid, asset = seed_candidate(client, m)
    client.post(f"/api/v1/review-issues/{cid}/resolve", json={"revision": 1, "action": "accepted"})
    snap = client.post(f"/api/v1/meetings/{m['id']}/snapshots", json={"revision": 2}).json()["id"]
    with transaction() as db:
        evidence = db.execute("SELECT id FROM evidence WHERE candidate_id=?", (cid,)).fetchone()[0]
    media = f"/api/v1/assets/{asset}/audio"
    response = client.get(media, headers={"range": "bytes=0-3"})
    assert response.status_code == 206 and response.content == b"RIFF"
    assert client.get(media, headers={"range": "bytes=999999999-"}).status_code == 416
    client.post(
        "/api/v1/accounts",
        json={"name": "denied-admin", "password": "synthetic-other-password", "role": "admin"},
    )
    client.delete("/api/v1/sessions/current")
    client.headers.pop("x-csrf-token")
    login = client.post(
        "/api/v1/sessions", json={"name": "denied-admin", "password": "synthetic-other-password"}
    )
    client.headers["x-csrf-token"] = login.json()["csrf"]
    for path in [
        f"meetings/{m['id']}/stream",
        f"meetings/{m['id']}/transcript?q=Elena",
        f"segments/{sid}",
        f"segments/{sid}/history",
        f"items/{cid}/history",
        f"evidence/{evidence}/audio",
        f"assets/{asset}/audio",
        f"snapshots/{snap}/exports/html",
        f"snapshots/{snap}/exports/json",
        f"snapshots/{snap}/exports/pdf",
        f"snapshots/{snap}/deliveries",
    ]:
        result = client.get("/api/v1/" + path, headers={"range": "bytes=0-3"})
        assert result.status_code == 404, (path, result.status_code)
        assert "Elena" not in result.text
    assert client.get("/api/v1/actions").json() == []


@pytest.mark.parametrize("revocation", ["membership", "logout", "expired"])
def test_live_stream_stops_after_authorization_revocation(client, monkeypatch, revocation):
    import asyncio
    from services.api.main import stream

    m = new_meeting(client)
    current = client.get("/api/v1/me").json()
    token = client.cookies.get("mom_session")

    class Request:
        cookies = {"mom_session": token}

        async def is_disconnected(self):
            return False

    async def no_wait(_):
        pass

    monkeypatch.setattr("services.api.main.asyncio.sleep", no_wait)

    async def exercise():
        response = await stream(m["id"], Request(), current)
        iterator = response.body_iterator
        assert await anext(iterator) == "data: []\n\n"
        with transaction() as db:
            if revocation == "membership":
                db.execute("DELETE FROM members WHERE meeting_id=? AND user_id=?", (m["id"], current["id"]))
            elif revocation == "logout":
                db.execute("DELETE FROM sessions WHERE id=?", (token,))
            else:
                db.execute("UPDATE sessions SET expires=0 WHERE id=?", (token,))
        with pytest.raises(StopAsyncIteration):
            await anext(iterator)

    asyncio.run(exercise())


def test_invalid_uploads_never_create_assets_and_names_cannot_escape(client):
    m = new_meeting(client)
    url = f"/api/v1/meetings/{m['id']}/uploads"
    assert (
        client.post(
            url, files={"file": ("attack.html", b"<script>alert(1)</script>", "audio/wav")}
        ).status_code
        == 400
    )
    bad = client.post(url, files={"file": ("attack.wav", b"not audio", "audio/wav")})
    assert bad.status_code == 400 and bad.json()["code"] == "audio_decode_failed"
    with transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0
    valid = client.post(url, files={"file": ("../../escape.wav", audio(), "audio/wav")})
    assert valid.status_code == 200
    from pathlib import Path

    with transaction() as db:
        saved = Path(db.execute("SELECT path FROM assets").fetchone()[0]).resolve()
    assert saved.is_relative_to((config.DATA / "audio" / m["id"]).resolve())
    assert not (config.DATA / "escape.wav").exists()


def test_minutes_escape_untrusted_source_and_metadata(client):
    m = new_meeting(client)
    _, cid, _ = seed_candidate(client, m)
    payload = '<img src="https://attacker.invalid/x" onerror="alert(1)">'
    with transaction() as db:
        db.execute("UPDATE meetings SET title=? WHERE id=?", (payload, m["id"]))
        body = json.loads(db.execute("SELECT body FROM candidates WHERE id=?", (cid,)).fetchone()[0])
        body["text"] = payload
        db.execute("UPDATE candidates SET body=? WHERE id=?", (canonical(body), cid))
    client.post(f"/api/v1/review-issues/{cid}/resolve", json={"revision": 1, "action": "accepted"})
    snap = client.post(f"/api/v1/meetings/{m['id']}/snapshots", json={"revision": 2}).json()["id"]
    response = client.get(f"/api/v1/snapshots/{snap}/exports/html")
    assert response.status_code == 200
    assert payload not in response.text and "&lt;img" in response.text
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_restore_retains_evidence_approval_audio_and_delivery_identity(client, tmp_path, monkeypatch):
    from scripts.mom import backup, restore
    from services.api.db import migrate

    m = new_meeting(client)
    sid, cid, asset = seed_candidate(client, m)
    client.post(f"/api/v1/review-issues/{cid}/resolve", json={"revision": 1, "action": "accepted"})
    snap = client.post(f"/api/v1/meetings/{m['id']}/snapshots", json={"revision": 2}).json()["id"]
    client.post(f"/api/v1/snapshots/{snap}/approve", json={"revision": 2})
    group = client.get("/api/v1/recipient-groups").json()[0]
    body = {"group_id": group["id"], "group_version": group["version"]}
    delivery = client.post(f"/api/v1/snapshots/{snap}/deliveries", json=body).json()["id"]
    before = client.get(f"/api/v1/snapshots/{snap}/exports/json").json()
    saved = tmp_path.parent / (tmp_path.name + "-backup")
    backup(saved)
    monkeypatch.setattr(config, "DATA", tmp_path.parent / (tmp_path.name + "-restored"))
    restore(saved)
    migrate()
    assert client.get(f"/api/v1/snapshots/{snap}/exports/json").json() == before
    assert client.get(f"/api/v1/assets/{asset}/audio").content[:4] == b"RIFF"
    assert client.get(f"/api/v1/segments/{sid}").json()["text"] == "Elena sends the report. Confirmed."
    assert client.post(f"/api/v1/snapshots/{snap}/deliveries", json=body).json()["id"] == delivery
    with transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 1


@pytest.mark.parametrize(
    ("suffix", "codec"),
    [(".mp3", "libmp3lame"), (".m4a", "aac"), (".ogg", "libopus"), (".flac", "flac"), (".webm", "libopus")],
)
def test_supported_formats_decode_real_audio_with_sample_clock(client, tmp_path, suffix, codec):
    import subprocess

    source = tmp_path / "input.wav"
    source.write_bytes(audio())
    encoded = tmp_path / ("encoded" + suffix)
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(source), "-c:a", codec, str(encoded)],
        check=True,
        timeout=30,
    )
    m = new_meeting(client)
    result = client.post(
        f"/api/v1/meetings/{m['id']}/uploads",
        files={"file": (encoded.name, encoded.read_bytes(), "application/octet-stream")},
    )
    assert result.status_code == 200, result.text
    meta = result.json()
    assert meta["sample_rate"] == 16000
    # Lossy formats may retain codec padding. Canonical clock describes actual decoded PCM.
    assert 31000 <= meta["samples"] <= 34000
    saved = client.get(f"/api/v1/assets/{meta['id']}/audio")
    with wave.open(io.BytesIO(saved.content)) as w:
        assert w.getnframes() == meta["samples"] and w.getframerate() == 16000
        assert w.getnchannels() == 1 and w.getsampwidth() == 2


def test_upload_duration_and_size_limits_are_enforced(client, monkeypatch):
    m = new_meeting(client)
    url = f"/api/v1/meetings/{m['id']}/uploads"
    monkeypatch.setattr(config, "MAX_SECONDS", 1)
    assert (
        client.post(url, files={"file": ("too-long.wav", audio(), "audio/wav")}).json()["code"]
        == "audio_decode_failed"
    )
    monkeypatch.setattr(config, "MAX_SECONDS", 7200)
    monkeypatch.setattr(config, "MAX_BYTES", 100)
    result = client.post(url, files={"file": ("too-big.wav", audio(), "audio/wav")})
    assert result.status_code == 413 and result.json()["code"] == "upload_too_large"
    with transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0


def test_t22_overlapping_worker_results_and_replay_create_one_item_and_delivery(client, monkeypatch):
    from copy import deepcopy
    from services.worker import supervisor
    from tests.browser_fixture import fixture_stage

    m = new_meeting(client)
    upload = client.post(
        f"/api/v1/meetings/{m['id']}/uploads", files={"file": ("overlap.wav", audio(), "audio/wav")}
    ).json()
    queued = client.post(f"/api/v1/meetings/{m['id']}/jobs", json={"asset_id": upload["id"], "device": "cpu"})
    assert queued.status_code == 200, queued.text
    with transaction() as db:
        job = dict(db.execute("SELECT * FROM jobs WHERE id=?", (queued.json()["id"],)).fetchone())

    def overlapping(job, stage, spec):
        output = fixture_stage(job, stage, spec)
        if stage == "extract":
            duplicate = deepcopy(output["events"][0])
            duplicate["evidence"].reverse()
            duplicate["evidence"].append(deepcopy(duplicate["evidence"][0]))
            output["events"].append(duplicate)
        return output

    monkeypatch.setattr(supervisor, "run_stage", overlapping)
    supervisor.process(job)
    supervisor.process(job)
    with transaction() as db:
        rows = db.execute("SELECT id FROM candidates WHERE meeting_id=?", (m["id"],)).fetchall()
        assert len(rows) == 1
    revision = client.get(f"/api/v1/meetings/{m['id']}").json()["revision"]
    accepted = client.post(
        f"/api/v1/review-issues/{rows[0][0]}/resolve", json={"revision": revision, "action": "accepted"}
    )
    assert accepted.status_code == 200, accepted.text
    assert len(client.get(f"/api/v1/meetings/{m['id']}/items").json()["items"]) == 1
    revision = accepted.json()["revision"]
    snap = client.post(f"/api/v1/meetings/{m['id']}/snapshots", json={"revision": revision}).json()["id"]
    client.post(f"/api/v1/snapshots/{snap}/approve", json={"revision": revision})
    group = client.get("/api/v1/recipient-groups").json()[0]
    body = {"group_id": group["id"], "group_version": group["version"]}
    first = client.post(f"/api/v1/snapshots/{snap}/deliveries", json=body)
    second = client.post(f"/api/v1/snapshots/{snap}/deliveries", json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    with transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 1


def test_quantity_survives_review_snapshot_and_human_replacement(client):
    from services.api.quantities import enrich_quantity

    meeting = new_meeting(client)
    sid, cid, _ = seed_candidate(client, meeting)
    text = "Approve 16 chairs for Room C."
    with transaction() as db:
        body = json.loads(db.execute("SELECT body FROM candidates WHERE id=?", (cid,)).fetchone()[0])
        body.update(
            subject="Room C",
            category="decision",
            text=text,
            owner=None,
            value="16",
            evidence=[dict(segment_id=sid, revision=1, field="text", quote=text)],
        )
        enrich_quantity(body, {sid: {"text": text, "revision": 1}})
        db.execute("UPDATE segments SET text=?,raw=? WHERE id=?", (text, text, sid))
        db.execute(
            "UPDATE candidates SET subject=?,body=? WHERE id=?", (body["subject"], canonical(body), cid)
        )
        db.execute("DELETE FROM evidence WHERE candidate_id=?", (cid,))
    response = client.post(f"/api/v1/review-issues/{cid}/resolve", json={"revision": 1, "action": "accepted"})
    assert response.status_code == 200, response.text
    snapshot = client.post(f"/api/v1/meetings/{meeting['id']}/snapshots", json={"revision": 2})
    assert snapshot.status_code == 200, snapshot.text
    base = f"/api/v1/snapshots/{snapshot.json()['id']}/exports/"
    exported = client.get(base + "json").json()
    assert exported["items"][0]["quantity"] == body["quantity"]
    assert "16 chairs" in client.get(base + "html").text
    correction = client.post(
        f"/api/v1/items/{cid}/corrections",
        json={
            "revision": 2,
            "subject": "Room C",
            "category": "decision",
            "kind": "confirm",
            "text": text,
            "owner": None,
            "due": None,
            "condition": None,
            "value": "18 chairs",
            "reason": "Secretary correction based on reviewed notes",
            "resolved_issues": [],
        },
    )
    assert correction.status_code == 200, correction.text
    with transaction() as db:
        corrected = json.loads(
            db.execute("SELECT body FROM candidates WHERE id=?", (correction.json()["id"],)).fetchone()[0]
        )
    assert corrected["quantity"] is None
    # Immutable earlier exports keep their original literal quantity after correction.
    assert client.get(base + "json").json()["items"][0]["quantity"] == body["quantity"]


@pytest.mark.parametrize("boundary", [False, True])
def test_asr_disagreement_withholds_structured_quantity_through_review(client, monkeypatch, boundary):
    from services.worker import supervisor
    from services.api.quantities import enrich_quantity

    meeting = new_meeting(client)
    sid, _, asset = seed_candidate(client, meeting)
    text = "The protocol mentions 7 mg."
    with transaction() as db:
        db.execute(
            "UPDATE segments SET text=?, alternatives=?, raw=? WHERE id=?",
            (
                text,
                canonical([{"engine": "explicit test alternative", "text": "The protocol mentions 1 mg."}]),
                canonical({"boundary_review": boundary}),
                sid,
            ),
        )
    queued = client.post(f"/api/v1/meetings/{meeting['id']}/jobs", json={"asset_id": asset, "device": "cpu"})
    assert queued.status_code == 200, queued.text
    with transaction() as db:
        job = dict(db.execute("SELECT * FROM jobs WHERE id=?", (queued.json()["id"],)).fetchone())

    def fixture(job, stage, spec):
        if stage == "whisper":
            return {"segments": []}
        source = spec["segments"][0]
        event = {
            "subject": "protocol numeric fact",
            "category": "information",
            "kind": "inform",
            "text": text,
            "owner": None,
            "due": None,
            "raw_due": None,
            "condition": None,
            "value": "7 mg",
            "changed_fields": [],
            "uncertainties": [],
            "evidence": [
                {"segment_id": source["id"], "revision": source["revision"], "field": "text", "quote": text}
            ],
        }
        enrich_quantity(event, {source["id"]: source})
        assert event["quantity"]["unit"] == "mg"
        return {"events": [event]}

    monkeypatch.setattr(supervisor, "run_stage", fixture)
    supervisor.process(job)
    response = client.get(f"/api/v1/meetings/{meeting['id']}/items").json()
    item = next(c for c in response["candidates"] if c["subject"] == "protocol numeric fact")
    assert item["body"]["value"] is None and item["body"]["quantity"] is None
    assert any("processing boundary" in issue for issue in item["body"]["uncertainties"]) is boundary
    accepted = client.post(
        f"/api/v1/review-issues/{item['id']}/resolve",
        json={"revision": response["revision"], "action": "accepted"},
    )
    # The contract permits reviewed unresolved information, but not a resolved numeric claim.
    assert accepted.status_code == 200, accepted.text
    projected = client.get(f"/api/v1/meetings/{meeting['id']}/items").json()["items"]
    fact = next(i for i in projected if i["subject"] == "protocol numeric fact")
    assert fact["category"] == "information" and fact["status"] == "information"
    assert fact["value"] is None and fact["quantity"] is None
    assert any("Critical numeric value withheld" in issue for issue in fact["uncertainties"])


def test_templates_are_versioned_escaped_and_frozen_in_snapshots(client):
    templates = client.get("/api/v1/settings/templates").json()
    assert {t["classification"] for t in templates} == {"Administrative", "Medical", "Executive"}
    group = client.get("/api/v1/recipient-groups").json()[0]
    body = {
        "version": 0,
        "titles": {
            "en": "<script>unsafe</script>",
            "ro": "Proces-verbal sintetic",
            "ru": "Синтетический протокол",
        },
        "introduction": "Synthetic introduction",
        "recipient_group_id": group["id"],
    }
    path = "/api/v1/settings/templates/Administrative"
    saved = client.put(path, json=body)
    assert saved.status_code == 200 and saved.json()["version"] == 1
    assert client.put(path, json=body).status_code == 409
    meeting = new_meeting(client)
    snapshot = client.post(f"/api/v1/meetings/{meeting['id']}/snapshots", json={"revision": 1}).json()["id"]
    base = f"/api/v1/snapshots/{snapshot}/exports/"
    before = client.get(base + "json").json()
    assert before["template"]["recipient_group_id"] == group["id"]
    html = client.get(base + "html").text
    assert "<script>unsafe</script>" not in html and "&lt;script&gt;unsafe&lt;/script&gt;" in html
    assert "Synthetic introduction" in html
    changed = client.put(path, json={**body, "version": 1, "introduction": "Changed introduction"})
    assert changed.status_code == 200 and changed.json()["version"] == 2
    assert client.get(base + "json").json() == before
    assert client.get(base + "html").text == html
    snapshots = client.get(f"/api/v1/meetings/{meeting['id']}/snapshots").json()
    assert snapshots[0]["suggested_group_id"] == group["id"]
    current = client.post(f"/api/v1/meetings/{meeting['id']}/snapshots", json={"revision": 1}).json()["id"]
    assert current != snapshot
    assert client.get(f"/api/v1/snapshots/{current}/exports/json").json()["template"]["version"] == 2
    assert client.put(path, json={**body, "version": 2, "recipient_group_id": "missing"}).status_code == 409


def test_template_configuration_requires_admin_but_selection_is_readable(client):
    created = client.post(
        "/api/v1/accounts",
        json={"name": "template-reader", "password": "synthetic-reader-password", "role": "secretary"},
    )
    assert created.status_code == 200
    login = client.post(
        "/api/v1/sessions", json={"name": "template-reader", "password": "synthetic-reader-password"}
    )
    client.headers["x-csrf-token"] = login.json()["csrf"]
    assert client.get("/api/v1/settings/templates").status_code == 200
    response = client.put("/api/v1/settings/templates/Medical", json={"version": 0, "titles": {}})
    assert response.status_code == 403 and response.json()["code"] == "admin_required"
