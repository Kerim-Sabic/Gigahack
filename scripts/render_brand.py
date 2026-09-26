"""Render original vector brand assets with existing local fonts and Chromium."""
import base64
import html
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    brand = json.loads((ROOT / "config/brand.json").read_text(encoding="utf-8"))
    target = ROOT / "apps/web/public/brand"
    font = ROOT / "apps/web/node_modules/@fontsource/noto-sans/files/noto-sans-latin-600-normal.woff2"
    encoded = base64.b64encode(font.read_bytes()).decode()
    symbol = (target / "symbol.svg").read_text(encoding="utf-8")
    paths = symbol.split(">", 1)[1].removesuffix("\n").removesuffix("</svg>")
    lockup = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 304 72">'
        '<style>@font-face{font-family:NotavraWordmark;src:url(data:font/woff2;base64,'
        + encoded + ') format("woff2");font-weight:600}</style>'
        '<g transform="translate(4 4)">' + paths + '</g>'
        '<text x="86" y="51" font-family="NotavraWordmark,sans-serif" font-size="42" '
        'font-weight="600" fill="' + brand["ink"] + '">' + html.escape(brand["name"]) + '</text></svg>'
    )
    (target / "lockup.svg").write_text(lockup, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=1)
        for source, width, height, output in [
            (symbol, 512, 512, "symbol.png"),
            (symbol, 32, 32, "favicon.png"),
            (lockup, 1216, 288, "lockup.png"),
        ]:
            page.set_viewport_size({"width": width, "height": height})
            page.set_content('<style>html,body{margin:0;background:transparent}svg{width:100%;height:100%}</style>' + source)
            page.evaluate("() => document.fonts.ready")
            page.screenshot(path=str(target / output), omit_background=True)
        page.set_viewport_size({"width": 820, "height": 440})
        mono = (target / "symbol-mono.svg").read_text(encoding="utf-8")
        samples = ''.join(
            f'<figure><div style="width:{size}px;height:{size}px">{source}</div><figcaption>{label} {size}px</figcaption></figure>'
            for source, label in [(symbol, "Color"), (mono, "Mono")]
            for size in (16, 24, 32, 64)
        )
        page.set_content('<style>body{font:14px sans-serif;padding:28px;color:#183438}section{display:flex;gap:20px}figure{margin:14px 0;min-width:70px}figcaption{margin-top:16px;font-size:11px}svg{width:100%;height:100%}</style><div style="width:304px;height:72px">' + lockup + '</div><section>' + samples + '</section><p>Original vectors. Local Noto Sans. Transparent PNG exports.</p>')
        page.evaluate("() => document.fonts.ready")
        page.screenshot(path=str(ROOT / "docs/brand/size-proof.png"))
        browser.close()


if __name__ == "__main__":
    main()
