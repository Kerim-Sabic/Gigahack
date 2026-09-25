"""Actionable checks; a temporary data-volume probe verifies actual write access."""

import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile

from services.api import config


def checks(report):
    result = []

    def add(name, passed, action, detail=None, warning=False):
        result.append(
            {
                "name": name,
                "status": "pass" if passed else "warning" if warning else "fail",
                "action": None if passed else action,
                "detail": detail,
            }
        )

    add(
        "supported Python",
        sys.version_info[:2] in ((3, 11), (3, 12)),
        "Use the project environment with Python 3.11 or 3.12.",
        report["python"],
    )
    add("FFmpeg", report["ffmpeg"], "Install the documented local FFmpeg prerequisite and put it on PATH.")
    probe_root = config.DATA
    while not probe_root.exists():
        probe_root = probe_root.parent
    write_error = None
    try:
        with tempfile.TemporaryFile(dir=probe_root) as probe:
            probe.write(b"Secure MOM preflight")
            probe.flush()
            os.fsync(probe.fileno())
    except OSError as exc:
        write_error = type(exc).__name__
    add(
        "data volume write access",
        write_error is None,
        "Choose a writable MOM_DATA directory and check its OS permissions and free space.",
        {"probe": "temporary file write/flush; removed on close", "error": write_error},
    )
    add(
        "prepared interface",
        (config.ROOT / "apps/web/dist/index.html").is_file(),
        "Run npm ci and npm run build in apps/web during preparation.",
    )
    missing, mismatched = [], []
    lock = config.ROOT / "requirements.lock.txt"
    for line in lock.read_text().splitlines() if lock.is_file() else []:
        if "==" not in line or line.startswith("#"):
            continue
        name, expected = line.strip().split("==", 1)
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(name)
        else:
            if actual != expected:
                mismatched.append({"package": name, "expected": expected, "installed": actual})
    add(
        "pinned Python packages",
        lock.is_file() and not missing and not mismatched,
        "Prepare this environment from requirements.lock.txt; offline installations must use the prepared wheel kit.",
        {"missing": missing, "mismatched": mismatched},
    )
    manifest = config.ROOT / "manifests/models.lock.json"
    try:
        models = json.loads(manifest.read_text())
    except (OSError, ValueError):
        models = {}
    for name in ("whisper", "qwen"):
        files = models.get(name, {}).get("files", {})
        absent = [relative for relative in files if not (config.MODELS / name / relative).is_file()]
        report["models"][name] = bool(files) and not absent
        add(
            name + " model files",
            report["models"][name],
            "Run python -m scripts.mom prepare-models during online preparation; then verify-assets.",
            {
                "missing": absent,
                "checksum_check": "Startup/verify-assets verifies complete hashes; doctor checks presence only.",
            },
        )
    suffix = ".exe" if os.name == "nt" else ""
    for folder, binary in (("llama", "llama-server"), ("mailpit", "mailpit")):
        found = list((config.ROOT / ".runtime/tools" / folder).rglob(binary + suffix))
        add(binary, bool(found), "Run python -m scripts.mom prepare-tools during online preparation.")
    browser = None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = Path(p.chromium.executable_path).is_file()
    except Exception:
        browser = False
    add(
        "prepared PDF/browser runtime",
        browser,
        "Install the pinned Playwright Chromium browser during online preparation, using the same PLAYWRIGHT_BROWSERS_PATH as runtime.",
    )
    add(
        "NVIDIA GPU visible",
        bool(report["gpu"]),
        "Check the NVIDIA driver and nvidia-smi. GPU processing is unavailable; use an explicitly selected CPU profile only if appropriate.",
    )
    add(
        "disk reserve",
        report["disk_free_bytes"] >= 5 * 1024**3,
        "Free at least 5 GiB on the application volume before processing; longer audio/backups need additional space.",
        report["disk_free_bytes"],
    )
    add(
        "target RAM capacity",
        report["ram_bytes"] >= 23 * 1024**3,
        "The planned laptop profile expects 24 GB RAM. Measure an alternative profile before relying on it.",
        report["ram_bytes"],
        warning=True,
    )
    occupied = [port for port, state in report["ports"].items() if state == "occupied"]
    add(
        "service ports",
        not occupied,
        "If Secure MOM is already running this is expected. Otherwise stop the conflicting service before starting; do not kill unrelated processes.",
        occupied,
        warning=True,
    )
    return result
