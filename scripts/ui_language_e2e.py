"""Real persisted UI languages and API error rendering; original evidence must not change."""

import json
import os

from playwright.sync_api import expect, sync_playwright

from services.api.config import DATA


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.goto("http://127.0.0.1:8765")
        page.get_by_label("Username", exact=True).fill(os.environ["MOM_QUALIFY_USER"])
        page.get_by_label("Password (12+ characters)", exact=True).fill(os.environ["MOM_QUALIFY_PASSWORD"])
        page.get_by_role("button", name="Continue").click()
        expect(page.locator("#language")).to_be_visible()
        meetings = page.request.get("http://127.0.0.1:8765/api/v1/meetings").json()
        meeting = next(
            m for m in meetings if m["status"] == "awaiting_review" and m["title"].startswith("Synthetic")
        )
        page.goto("http://127.0.0.1:8765/?meeting=" + meeting["id"])
        expect(page.locator("blockquote").first).to_be_visible(timeout=10000)
        original = page.locator("blockquote").first.inner_text()
        try:
            for lang, error in [
                ("ro", "O adresă nu aparține domeniilor permise."),
                ("ru", "Адрес не относится к разрешённым доменам получателей."),
            ]:
                page.locator("#language").select_option(lang)
                expect(page.locator("html")).to_have_attribute("lang", lang)
                page.reload()
                expect(page.locator("html")).to_have_attribute("lang", lang)
                expect(page.locator("blockquote").first).to_have_text(original)
                page.screenshot(path=str(DATA / "proofs" / f"review-{lang}.png"), full_page=True)
                page.locator("nav button").nth(3).click()
                form = page.locator("form:has(textarea[name=addresses])")
                form.locator("input[name=name]").fill("Synthetic invalid recipient test")
                form.locator("textarea[name=addresses]").fill("person@outside.invalid")
                form.get_by_role("button").click()
                expect(page.get_by_text(error, exact=True)).to_be_visible()
                page.goto("http://127.0.0.1:8765/?meeting=" + meeting["id"])
                expect(page.locator("blockquote").first).to_have_text(original)
        finally:
            page.locator("#language").select_option("en")
            expect(page.locator("html")).to_have_attribute("lang", "en")
            browser.close()
    report = {
        "languages": ["ro", "ru"],
        "checks": ["preference_persisted", "source_quote_unchanged", "localized_recipient_error"],
        "native_linguistic_review": "not performed",
    }
    (DATA / "proofs/ui-languages.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
