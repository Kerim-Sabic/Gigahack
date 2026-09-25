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
        page.get_by_role("button", name="＋ New meeting", exact=True).click()
        page.get_by_label("Meeting title").fill("Synthetic end-to-end qualification")
        page.get_by_label("Participants, one per line").fill("Elena\nAndrei")
        page.get_by_role("button", name="Create meeting", exact=True).click()
        page.get_by_label("Upload audio", exact=True).set_input_files(str(fixture))
        page.get_by_role("button", name="Process audio", exact=True).wait_for(timeout=30000)
        page.get_by_role("button", name="Process audio", exact=True).click()
        expect(page.get_by_text("awaiting review", exact=True)).to_be_visible(timeout=240000)
        expect(page.locator(".itemlist button").first).to_be_visible(timeout=10000)
        page.screenshot(path=str(proof / "review-1366.png"), full_page=True)
        for _ in range(20):
            button = page.get_by_role("button", name="Accept", exact=True)
            if button.is_enabled():
                button.click()
                expect(button).to_be_disabled(timeout=10000)
            pending = page.locator(".itemlist button").filter(has_text="unreviewed")
            if pending.count() == 0:
                break
            pending.first.click()
        page.get_by_role("tab", name="Minutes", exact=True).click()
        page.get_by_role("button", name="Create preview", exact=True).click()
        page.get_by_role("button", name="Approve version", exact=True).click()
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
        browser.close()
    report = {
        "kind": "fixture-inference-browser" if fixture_inference else "real-model-browser-synthetic",
        "elapsed_seconds": time.time() - started,
        "checks": [
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
