"""Real browser, API, worker and SMTP workflow using explicitly synthetic input."""

import json
import os
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright, expect

from services.api.config import DATA


def main(*, fixture_inference=False):
    fixture = Path(os.environ.get("MOM_SYNTHETIC_AUDIO", DATA / "smoke/synthetic.wav")).resolve()
    if not fixture.exists():
        raise SystemExit("Set MOM_SYNTHETIC_AUDIO to a synthetic speech fixture.")
    proof = DATA / "proofs"
    proof.mkdir(exist_ok=True, parents=True)
    started = time.time()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://127.0.0.1:8765")
        page.get_by_label("Username", exact=True).fill(os.environ["MOM_QUALIFY_USER"])
        page.get_by_label("Password (12+ characters)", exact=True).fill(os.environ["MOM_QUALIFY_PASSWORD"])
        page.get_by_role("button", name="Continue").click()
        if fixture_inference:
            page.get_by_role("button", name="Settings", exact=True).click()
            page.get_by_label("New group name", exact=True).fill("CI reviewers")
            page.get_by_label("Addresses, one per line", exact=True).fill("reviewers@secure-mom.test")
            page.get_by_role("button", name="Save recipient group", exact=True).click()
            expect(page.get_by_text("Saved on this computer.", exact=True)).to_be_visible()
            page.get_by_text("Edit recipient group: CI reviewers", exact=True).click()
            page.locator("details[open]").get_by_label("Updated addresses, one per line", exact=True).fill(
                "reviewers@secure-mom.test"
            )
            page.get_by_role("button", name="Save group changes", exact=True).last.click()
            expect(
                page.get_by_text("CI reviewers · version 2: reviewers@secure-mom.test", exact=True)
            ).to_be_visible()
            page.get_by_label("Username", exact=True).fill("fixture-viewer")
            page.get_by_label("Password", exact=True).fill("synthetic-viewer-password")
            page.get_by_label("Role", exact=True).select_option("viewer")
            page.get_by_role("button", name="Create account", exact=True).click()
            expect(page.get_by_text("Saved on this computer.", exact=True)).to_be_visible()
            page.get_by_role("button", name="Templates", exact=True).click()
            template_card = page.locator("section.card").filter(
                has=page.get_by_role("heading", name="Administrative", exact=False)
            )
            template_card.get_by_label("English document heading", exact=True).fill(
                "Synthetic template minutes"
            )
            template_card.get_by_label("Document introduction", exact=True).fill(
                "Synthetic configured introduction"
            )
            template_card.get_by_label("Suggested recipient group", exact=True).select_option(
                label="CI reviewers"
            )
            template_card.get_by_role("button", name="Save template", exact=True).click()
            expect(template_card.get_by_text("Saved on this computer.", exact=True)).to_be_visible()
            page.get_by_role("button", name="Meetings", exact=True).click()
        page.get_by_role("button", name="＋ New meeting", exact=True).click()
        page.get_by_label("Meeting title").fill("Synthetic end-to-end qualification")
        page.get_by_label("Meeting date", exact=True).fill("2026-09-25")
        page.get_by_label("Timezone", exact=True).fill("Europe/Chisinau")
        page.get_by_label("Participants, one per line").fill("Elena\nAndrei")
        page.get_by_role("button", name="Create meeting", exact=True).click()
        if fixture_inference:
            page.get_by_text("Meeting details and access", exact=True).click()
            page.get_by_label("Date", exact=True).fill("2026-09-24")
            page.get_by_role("button", name="Save meeting details", exact=True).click()
            expect(page.locator(".pageheading .eyebrow")).to_contain_text("2026-09-24")
            page.get_by_label("Local account", exact=True).select_option(label="fixture-viewer · viewer")
            with page.expect_response(
                lambda r: r.url.endswith("/members") and r.request.method == "POST"
            ) as granted:
                page.get_by_role("button", name="Grant access", exact=True).click()
            assert granted.value.status == 200
            page.get_by_text("Meeting details and access", exact=True).click()
        page.get_by_label("Upload audio", exact=True).set_input_files(str(fixture))
        page.get_by_role("button", name="Process audio", exact=True).wait_for(timeout=30000)
        page.get_by_role("button", name="Process audio", exact=True).click()
        expect(page.locator(".pageheading .badge").first).to_have_text("awaiting review", timeout=240000)
        expect(page.locator(".itemlist button").first).to_be_visible(timeout=10000)
        if fixture_inference:
            checks = page.get_by_role("region", name="Audio passages to check")
            expect(checks.get_by_text("The second recognizer returned no text here.", exact=True)).to_be_visible()
            checks.get_by_role("button", name="Play passage", exact=False).click()
            page.wait_for_function("() => document.querySelector('audio').currentSrc.includes('/assets/') && document.querySelector('audio').readyState >= 2")
            page.evaluate("() => document.querySelector('audio').pause()")
            checks.get_by_text("Recovery hypothesis · shorter retry", exact=True).click()
            expect(checks.get_by_text("Synthetic recovery: cererea сегодня.", exact=True)).to_be_visible()
            checks.get_by_role("button", name="Play recovery context", exact=False).click()
            page.wait_for_function("() => document.querySelector('audio').readyState >= 2 && document.querySelector('audio').duration === 2")
            page.evaluate("() => document.querySelector('audio').pause()")
            page.get_by_role("tab", name="Transcript", exact=True).click()
            expect(page.get_by_text("Check the wording here against the audio; this passage crosses a processing boundary.", exact=True)).to_be_visible()
            page.get_by_role("tab", name="Decisions & actions", exact=True).click()
        page.screenshot(path=str(proof / "review-1366.png"), full_page=True)
        for _ in range(20):
            button = page.get_by_role("button", name="Accept", exact=True)
            if button.is_enabled():
                button.click()
                expect(page.locator(".detail .badge")).to_have_text("Review: accepted", timeout=10000)
                expect(button).to_be_disabled(timeout=10000)
            pending = page.locator(".itemlist button").filter(has_text="unreviewed")
            if pending.count() == 0:
                break
            pending.first.click()
        page.get_by_role("tab", name="Minutes", exact=True).click()
        page.get_by_role("button", name="Create preview", exact=True).click()
        page.get_by_role("button", name="Approve version", exact=True).click()
        if fixture_inference:
            expect(page.get_by_label("Recipient group", exact=True).locator("option:checked")).to_have_text(
                "CI reviewers"
            )
            expect(page.locator(".snapshot strong")).to_have_text("reviewers@secure-mom.test")
            snapshot_json = page.request.get(
                "http://127.0.0.1:8765" + page.get_by_role("link", name="JSON ↗").get_attribute("href")
            ).json()
            assert snapshot_json["audio_checks"][0]["count"] == 1
            assert snapshot_json["unresolved"].count("Source crosses an audio processing boundary; verify wording against the audio") == 1
            assert any("Automated audio flags" in warning for warning in snapshot_json["unresolved"])
            assert snapshot_json["template"]["version"] == 1
            assert snapshot_json["template"]["titles"]["en"] == "Synthetic template minutes"
            assert snapshot_json["template"]["introduction"] == "Synthetic configured introduction"
        send = page.get_by_role("button", name="Send approved version", exact=True)
        expect(send).to_be_enabled()
        send.click()
        expect(page.get_by_text("Local delivery: smtp accepted", exact=False)).to_be_visible(timeout=30000)
        pdf_url = page.get_by_role("link", name="PDF ↗").get_attribute("href")
        pdf = page.request.get("http://127.0.0.1:8765" + pdf_url)
        assert pdf.status == 200 and pdf.body().startswith(b"%PDF"), pdf.status
        page.screenshot(path=str(proof / "minutes-1366.png"), full_page=True)
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.screenshot(path=str(proof / "minutes-1920.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.set_viewport_size({"width": 683, "height": 384})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.get_by_role("link", name="Skip to content").focus()
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.tagName") in ("BUTTON", "A", "INPUT", "SELECT")
        messages = httpx.get("http://127.0.0.1:8025/api/v1/messages", trust_env=False).json()
        assert messages["total"] >= 1
        if fixture_inference:
            assert messages["messages"][0]["To"][0]["Address"] == "reviewers@secure-mom.test"
            page.set_viewport_size({"width": 1366, "height": 768})
            page.get_by_role("tab", name="Decisions & actions", exact=True).click()
            page.locator(".detail").get_by_text("Secretary amendment", exact=True).click()
            page.get_by_label("Topic / item key", exact=True).fill("maintenance report")
            page.get_by_label("Text", exact=True).fill("Synthetic reviewed maintenance report")
            page.get_by_label("Reason for amendment", exact=True).fill("Synthetic browser correction reason")
            page.get_by_role("button", name="Save reviewed amendment", exact=True).click()
            history = page.locator(".evidence")
            history.get_by_text("Secretary amendment", exact=True).click()
            expect(history.get_by_text("Synthetic browser correction reason", exact=True)).to_be_visible()
            expect(history.get_by_text("Synthetic reviewed maintenance report", exact=True)).to_be_visible()
            page.screenshot(path=str(proof / "amendment-history.png"), full_page=True)
        browser.close()
    report = {
        "kind": "fixture-inference-browser" if fixture_inference else "real-model-browser-synthetic",
        "elapsed_seconds": time.time() - started,
        "checks": (
            [
                "metadata_edit",
                "account_create",
                "member_grant",
                "recipient_group_edit",
                "template_configuration",
                "template_snapshot_freezing",
                "audio_check_playback",
                "audio_check_snapshot_warning",
                "deduplicated_source_warnings",
                "suggested_recipient_group",
                "manual_topic_link",
                "retained_amendment_history",
            ]
            if fixture_inference
            else []
        )
        + [
            "login",
            "create",
            "upload",
            "fixture_asr" if fixture_inference else "real_asr",
            "fixture_extraction" if fixture_inference else "real_extraction",
            "review",
            "snapshot",
            "approval",
            "smtp_accepted",
            "mailpit_receipt",
            "pdf",
            "responsive_layout",
            "keyboard_focus",
        ],
        "page_errors": errors,
        "human_multilingual_accuracy": "not measured",
        "target_laptop": "not run",
    }
    (proof / "browser-e2e.json").write_text(json.dumps(report, indent=2))
    assert not errors, errors
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
