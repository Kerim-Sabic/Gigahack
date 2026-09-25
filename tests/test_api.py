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
