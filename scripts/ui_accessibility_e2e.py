"""Actual Chromium 200% page zoom and fixture viewer controls."""

import json
import os

from playwright.sync_api import expect, sync_playwright

from services.api.config import DATA


def main():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(DATA / "zoom-browser-profile"),
            channel="chromium",
            headless=True,
            no_viewport=True,
            args=["--window-size=1366,768"],
        )
        try:
            page = context.pages[0]
            # Use Chromium's real page-zoom control, not CSS zoom or a small viewport.
            page.goto("chrome://settings/appearance")
            page.locator("select#zoomLevel").select_option(label="200%")
            page.goto("http://127.0.0.1:8765")
            metrics = page.evaluate("({width:innerWidth,outer:outerWidth,ratio:devicePixelRatio})")
            assert metrics["ratio"] == 2 and 650 <= metrics["width"] <= 700, metrics
            page.get_by_label("Username", exact=True).fill(os.environ["MOM_QUALIFY_USER"])
            page.get_by_label("Password (12+ characters)", exact=True).fill(
                os.environ["MOM_QUALIFY_PASSWORD"]
            )
            page.get_by_role("button", name="Continue").click()
            expect(page.locator("#language")).to_be_visible()
            meetings = page.request.get("http://127.0.0.1:8765/api/v1/meetings").json()
            meeting = next(m for m in meetings if m["title"].startswith("Synthetic"))
            page.goto("http://127.0.0.1:8765/?meeting=" + meeting["id"])
            expect(page.locator("blockquote").first).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.get_by_role("link", name="Skip to content").focus()
            page.keyboard.press("Enter")
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement.tagName") in (
                "BUTTON",
                "A",
                "INPUT",
                "SELECT",
                "SUMMARY",
            )
            page.get_by_role("tab", name="Minutes", exact=True).click()
            expect(page.locator(".snapshot").first).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.get_by_role("button", name="Sign out", exact=True).click()
            page.get_by_label("Username", exact=True).fill("fixture-viewer")
            page.get_by_label("Password (12+ characters)", exact=True).fill("synthetic-viewer-password")
            page.get_by_role("button", name="Continue").click()
            expect(page.locator("#language")).to_be_visible()
            expect(page.get_by_role("button", name="＋ New meeting", exact=True)).to_have_count(0)
            page.goto("http://127.0.0.1:8765/?meeting=" + meeting["id"])
            expect(page.locator("blockquote").first).to_be_visible()
            expect(page.get_by_role("button", name="Accept", exact=True)).to_be_disabled()
            expect(page.get_by_role("button", name="Exclude", exact=True)).to_be_disabled()
            expect(page.locator("fieldset.mutation-controls input[type=file]")).to_be_disabled()
            expect(page.get_by_role("button", name="Save reviewed amendment", exact=True)).to_have_count(0)
            report = {
                "checks": [
                    "actual_200_percent_zoom",
                    "review_and_minutes_no_horizontal_overflow",
                    "keyboard_focus",
                    "viewer_read_only_controls",
                ],
                "metrics": metrics,
                "scope": "Prepared Chromium DOM/layout checks; not a complete assistive-technology audit",
                "zoom_visual_capture": "Not qualified: headless zoom screenshots were blank/cropped; normal-scale screenshots are separate.",
            }
            (DATA / "proofs/accessibility.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
        finally:
            context.close()


if __name__ == "__main__":
    main()
