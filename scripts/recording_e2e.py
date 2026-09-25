"""Exercise the real AudioWorklet with explicitly synthetic Chromium microphone audio."""

import json
import os
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from services.api.config import DATA


def main():
    fixture = Path(os.environ.get("MOM_SYNTHETIC_AUDIO", DATA / "smoke/synthetic.wav")).resolve()
    seconds = int(os.environ.get("MOM_CAPTURE_SECONDS", "305"))
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                f"--use-file-for-fake-audio-capture={fixture}",
            ]
        )
        context = browser.new_context(permissions=["microphone"])
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://127.0.0.1:8765")
        page.get_by_label("Username", exact=True).fill(os.environ["MOM_QUALIFY_USER"])
        page.get_by_label("Password (12+ characters)", exact=True).fill(os.environ["MOM_QUALIFY_PASSWORD"])
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("button", name="＋ New meeting", exact=True).click()
        title = f"Synthetic microphone recovery {time.time_ns()}"
        page.get_by_label("Meeting title").fill(title)
        page.get_by_role("button", name="Create meeting", exact=True).click()
        page.get_by_role("button", name="Record microphone", exact=True).click()
        expect(page.get_by_role("button", name="Pause", exact=True)).to_be_visible()
        # Keep the real browser event loop running during capture; no accelerated clock.
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            page.wait_for_timeout(min(1000, max(1, (deadline - time.monotonic()) * 1000)))
        page.get_by_role("button", name="Pause", exact=True).click()
        page.wait_for_timeout(1200)
        page.get_by_role("button", name="Resume", exact=True).click()
        page.wait_for_timeout(2500)
        page.get_by_role("button", name="Stop and save", exact=True).click()
        expect(page.get_by_role("button", name="Process audio", exact=True)).to_be_visible(timeout=30000)
        meetings = page.request.get("http://127.0.0.1:8765/api/v1/meetings").json()
        meeting = next(x for x in meetings if x["title"] == title)
        detail_url = f"http://127.0.0.1:8765/api/v1/meetings/{meeting['id']}"
        detail = page.request.get(detail_url).json()
        duration = detail["assets"][0]["samples"] / detail["assets"][0]["sample_rate"]
        assert duration >= seconds - 2, duration
        # Abrupt browser closure: only acknowledged chunks may be recovered.
        page.get_by_role("button", name="Record microphone", exact=True).click()
        page.wait_for_timeout(6500)
        page.close(run_before_unload=False)
        page = context.new_page()
        page.goto("http://127.0.0.1:8765")
        page.get_by_role("button", name=title, exact=False).click()
        expect(page.get_by_role("button", name="Seal acknowledged audio", exact=True)).to_be_visible(
            timeout=10000
        )
        before = page.request.get(detail_url).json()
        pending = next(x for x in before["recordings"] if x["state"] == "recording")
        assert pending["acknowledged_samples"] > 0
        page.get_by_role("button", name="Seal acknowledged audio", exact=True).click()
        expect(page.get_by_role("button", name="Seal acknowledged audio", exact=True)).to_have_count(0)
        after = page.request.get(detail_url).json()
        assert len(after["assets"]) == 2
        assert not errors, errors
        proof = {
            "kind": "synthetic-browser-microphone",
            "capture_seconds": seconds,
            "saved_source_seconds": duration,
            "checks": [
                "AudioWorklet",
                "durable_chunk_ack",
                "pause_resume",
                "stop_flush",
                "browser_loss",
                "seal_acknowledged_audio",
            ],
            "physical_microphone": "not measured",
            "page_errors": errors,
        }
        (DATA / "proofs/recording-e2e.json").write_text(json.dumps(proof, indent=2))
        print(json.dumps(proof, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
