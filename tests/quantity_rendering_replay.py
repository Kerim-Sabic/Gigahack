"""Replay captured synthetic model artifacts through real review/JSON/PDF presentation.

No new inference or audio accuracy is claimed. This test-only harness is never imported
by production. The source evaluation must contain a passing T10 check.
"""

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import uuid
import wave


def main(evaluation):
    root = Path(__file__).resolve().parents[1]
    evaluation = Path(evaluation).resolve()
    results = json.loads((evaluation / "text-results.json").read_text(encoding="utf-8"))
    assert next(r for r in results if r["id"] == "T10")["status"].startswith("PASS")
    spec = json.loads((evaluation / "T10-input.json").read_text(encoding="utf-8"))
    observed = json.loads((evaluation / "T10-output.json").read_text(encoding="utf-8"))
    data = root / ".runtime" / ("quantity-replay-" + uuid.uuid4().hex)
    data.mkdir()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    os.environ.update(MOM_DATA=str(data), MOM_ORIGIN=origin)
    from services.api.db import transaction, uid, canonical
    from services.api.domain import Candidate, validate_evidence
    from services.worker.supervisor import kill_tree
    from playwright.sync_api import sync_playwright, expect
    import httpx

    process = None
    try:
        with (data / "api.log").open("wb") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "services.api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                ],
                cwd=root,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        password = secrets.token_urlsafe(24)
        with httpx.Client(base_url=origin, trust_env=False) as client:
            for _ in range(40):
                if process.poll() is not None:
                    raise RuntimeError("Test API exited")
                try:
                    if client.get("/api/v1/setup").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.25)
            response = client.post("/api/v1/setup", json={"name": "quantity-reviewer", "password": password})
            response.raise_for_status()
            client.headers["x-csrf-token"] = response.json()["csrf"]
            response = client.post(
                "/api/v1/meetings",
                json={
                    "title": "Synthetic quantity rendering replay",
                    "date": spec["meeting"]["date"],
                    "participants": ["Synthetic reviewer"],
                },
            )
            response.raise_for_status()
            meeting = response.json()["id"]
            stream = io.BytesIO()
            with wave.open(stream, "wb") as wav:
                wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                wav.writeframes(bytes(64000))
            response = client.post(
                f"/api/v1/meetings/{meeting}/uploads",
                files={"file": ("rendering-placeholder.wav", stream.getvalue(), "audio/wav")},
            )
            response.raise_for_status()
            asset = response.json()["id"]
        mapping = {s["id"]: uid() for s in spec["segments"]}
        sources = {mapping[s["id"]]: {**s, "id": mapping[s["id"]]} for s in spec["segments"]}
        with transaction() as db:
            for segment in sources.values():
                db.execute(
                    "INSERT INTO segments(id,meeting_id,asset_id,revision,start,end,text,raw) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        segment["id"],
                        meeting,
                        asset,
                        segment["revision"],
                        segment["start"],
                        segment["end"],
                        segment["text"],
                        canonical(
                            {
                                "provenance": "captured synthetic text-model evaluation; silence is playback placeholder"
                            }
                        ),
                    ),
                )
            for index, original in enumerate(observed["events"]):
                event = copy.deepcopy(original)
                for ref in event["evidence"] + (event.get("quantity") or {}).get("evidence", []):
                    ref["segment_id"] = mapping[ref["segment_id"]]
                refs = validate_evidence(Candidate.model_validate(event), sources)
                ident = uid()
                db.execute(
                    "INSERT INTO candidates(id,meeting_id,subject,body,source_order,created) VALUES(?,?,?,?,?,?)",
                    (ident, meeting, event["subject"], canonical(event), index, time.time()),
                )
                for ref in refs:
                    db.execute(
                        "INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            uid(),
                            meeting,
                            ident,
                            ref["segment_id"],
                            ref["revision"],
                            ref["field"],
                            ref["quote"],
                            ref["start"],
                            ref["end"],
                        ),
                    )
            db.execute("UPDATE meetings SET status='awaiting_review' WHERE id=?", (meeting,))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.goto(origin)
            page.get_by_label("Username", exact=True).fill("quantity-reviewer")
            page.get_by_label("Password (12+ characters)", exact=True).fill(password)
            page.get_by_role("button", name="Continue", exact=False).click()
            page.get_by_role("button", name="Templates", exact=True).click()
            card = page.locator("section.card").filter(
                has=page.get_by_role("heading", name="Administrative", exact=False)
            )
            card.get_by_label("English document heading", exact=True).fill("Synthetic quantity minutes")
            card.get_by_label("Document introduction", exact=True).fill(
                "Synthetic saved template introduction"
            )
            card.get_by_label("Suggested recipient group", exact=True).select_option(index=1)
            card.get_by_role("button", name="Save template", exact=True).click()
            expect(card.get_by_text("Saved on this computer.", exact=True)).to_be_visible()
            page.get_by_role("button", name="Meetings", exact=True).click()
            page.get_by_role("button", name="Synthetic quantity rendering replay", exact=False).click()
            expect(page.locator(".itemlist button").first).to_be_visible()
            for index in range(page.locator(".itemlist button").count()):
                page.locator(".itemlist button").nth(index).click()
                page.get_by_role("button", name="Accept", exact=True).click()
                expect(page.get_by_role("button", name="Accept", exact=True)).to_be_disabled()
            expect(page.locator(".detail .field").filter(has_text="value")).to_contain_text("25 beds")
            page.locator(".detail .field").filter(has_text="value").click()
            expect(page.locator(".evidence blockquote").first).to_have_text("25 beds")
            page.screenshot(path=str(data / "quantity-review.png"), full_page=True)
            page.get_by_role("tab", name="Minutes", exact=True).click()
            page.get_by_role("button", name="Create preview", exact=True).click()
            link = page.get_by_role("link", name="JSON ↗")
            expect(link).to_be_visible()
            snapshot = page.request.get(origin + link.get_attribute("href")).json()
            assert snapshot["template"]["version"] == 1
            assert snapshot["template"]["titles"]["en"] == "Synthetic quantity minutes"
            assert snapshot["template"]["introduction"] == "Synthetic saved template introduction"
            item = snapshot["items"][0]
            assert (item["status"], item["category"], item["value"]) == ("confirmed", "decision", "25 beds")
            assert item["quantity"]["amount"] == "25" and item["quantity"]["unit"] == "beds"
            assert "ward a" in item["quantity"]["scope"].casefold()
            assert any(e["value"] == "20 beds" for e in item["history"])
            (data / "snapshot.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            pdf = page.request.get(origin + page.get_by_role("link", name="PDF ↗").get_attribute("href"))
            assert pdf.status == 200 and pdf.body().startswith(b"%PDF")
            (data / "quantity.pdf").write_bytes(pdf.body())
            html = page.request.get(
                origin + page.get_by_role("link", name="HTML ↗").get_attribute("href")
            ).text()
            assert "25 beds" in html and "Ward A" in html
            (data / "quantity.html").write_text(html, encoding="utf-8")
            browser.close()
        report = {
            "scope": "captured real text-model output replay; real API/browser/review/rendering; no new ASR or inference",
            "source_evaluation": evaluation.name,
            "source_output_sha256": hashlib.sha256((evaluation / "T10-output.json").read_bytes()).hexdigest(),
            "checks": [
                "UI value",
                "UI literal source",
                "JSON quantity and scope",
                "immutable preview",
                "PDF response",
            ],
            "pdf_visual_and_text": "pending separate inspection",
        }
        (data / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(data)
    finally:
        if process:
            kill_tree(process.pid)


if __name__ == "__main__":
    main(sys.argv[1])
