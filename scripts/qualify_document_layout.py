"""Synthetic multilingual print-layout probe; no model or meeting approval claims."""
import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from services.api.minutes import render


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".runtime") / f"document-layout-{time.time_ns()}")
    out = parser.parse_args().output
    out.mkdir(parents=True, exist_ok=False)
    reports = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for language in ("en", "ro", "ru"):
                for count in (0, 1, 60):
                    key = f"{language}-{count}"
                    data = {
                        "meeting": {"title": "Synthetic layout / Ședință / Совещание", "date": "", "timezone": "",
                                    "classification": "Administrative", "revision": 7, "language": language},
                        "participants": ["Elena Ștefănescu", "Александр Константинович"] if count else [],
                        "items": [], "unresolved": ["Synthetic unresolved matter: date and owner are unknown."] if count else [],
                    }
                    for i in range(count):
                        data["items"].append({
                            "subject": f"synthetic-{i}",
                            "text": f"{i + 1}. Verificăm documentele și termenul. Проверяем документы и срок. "
                                    + ("unbroken_reference_" * 14 if i == 7 else ""),
                            "owner": "Ștefănescu / Константинович", "due": None, "status": "confirmed",
                            "condition": None, "value": None, "history": [],
                        })
                    source = render(data)
                    (out / f"{key}.html").write_text(source, encoding="utf-8")
                    page = browser.new_page(viewport={"width": 794, "height": 1123})
                    requests = []
                    page.on("request", lambda request: requests.append(request.url))
                    page.route("**/*", lambda route: route.abort())
                    page.set_content(source)
                    page.emulate_media(media="print")
                    page.pdf(path=str(out / f"{key}.pdf"), format="A4", print_background=True)
                    width = page.evaluate("document.documentElement.scrollWidth")
                    rows = page.locator("tbody tr").count()
                    assert width <= 794, (key, "horizontal_overflow", width)
                    assert rows == count, (key, "missing_rows", rows)
                    assert not requests, (key, "unexpected_external_assets")
                    reports.append({"case": key, "rows": rows, "scroll_width": width, "external_requests": 0})
                    page.close()
        finally:
            browser.close()
    result = {"scope": "Synthetic DOM and A4 PDF generation; rendered pages still require visual inspection. Not physical printing or acoustic accuracy.", "cases": reports}
    (out / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), **result}, indent=2))


if __name__ == "__main__":
    main()
