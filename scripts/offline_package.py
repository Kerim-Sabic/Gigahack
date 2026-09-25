"""Prepare a platform-specific offline kit online; never include meeting state."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from services.api import config


INSTALLER = '''"""Run with the same Python minor version and OS used to prepare this kit."""
import hashlib, json, os, platform, subprocess, sys, venv
from pathlib import Path
root = Path(__file__).resolve().parent
manifest = json.loads((root / "kit.json").read_text())
if [sys.version_info.major, sys.version_info.minor] != manifest["python"] or platform.system() != manifest["platform"]:
    raise SystemExit("This kit requires its recorded Python minor version and operating system.")
for name, expected in manifest["files"].items():
    path = root / name
    if not path.is_file(): raise SystemExit("Missing kit file: " + name)
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise SystemExit("Kit checksum mismatch: " + name)
env = root / "application/.venv"
if env.exists(): raise SystemExit("Environment already exists; do not overwrite an existing installation.")
venv.create(env, with_pip=True)
python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-index", "--find-links", str(root / "wheels"), "-r", str(root / "application/requirements.lock.txt")], check=True)
print("Offline installation complete. Install the documented FFmpeg/driver prerequisites, then run scripts.mom start from application.")
'''


def copy_application(root, destination):
    """Explicit inclusion list prevents runtime data, credentials and Git metadata leaks."""
    for name in ["services", "scripts", "tests", "docs", "contracts", "manifests", "apps/web/dist"]:
        shutil.copytree(
            root / name, destination / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env")
        )
    for name in [
        "README.md",
        "AGENTS.md",
        "pyproject.toml",
        "requirements.lock.txt",
        "requirements-api.lock.txt",
        ".env.example",
    ]:
        shutil.copy2(root / name, destination / name)


def prepare(path):
    from scripts.mom import verify_assets
    import playwright

    if not path:
        raise SystemExit("prepare-offline requires --path to a new directory.")
    target = Path(path).resolve()
    if target.exists():
        raise SystemExit("Offline kit destination must not exist.")
    if platform.system() != "Windows":
        raise SystemExit(
            "Offline kit preparation is currently qualified only for Windows; Linux tooling is pending."
        )
    verify_assets()
    if not (config.ROOT / "apps/web/dist/index.html").exists():
        raise SystemExit("Build the frontend first.")
    browser_root = Path(
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH", Path(os.environ["LOCALAPPDATA"]) / "ms-playwright")
    )
    browser_spec = json.loads((Path(playwright.__file__).parent / "driver/package/browsers.json").read_text())
    browser_dirs = []
    for entry in browser_spec["browsers"]:
        if entry["name"] in ["chromium", "chromium-headless-shell", "ffmpeg", "winldd"]:
            folder = browser_root / f"{entry['name'].replace('-', '_')}-{entry['revision']}"
            if not folder.is_dir():
                raise SystemExit(f"Missing prepared browser component: {folder.name}")
            browser_dirs.append(folder)
    target.mkdir(parents=True)
    app = target / "application"
    copy_application(config.ROOT, app)
    shutil.copytree(config.MODELS, app / "models", ignore=shutil.ignore_patterns(".cache", ".git"))
    for name in ["llama", "mailpit"]:
        shutil.copytree(config.ROOT / ".runtime/tools" / name, app / ".runtime/tools" / name)
    for folder in browser_dirs:
        shutil.copytree(folder, app / ".runtime/browsers" / folder.name)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--disable-pip-version-check",
            "--only-binary=:all:",
            "--dest",
            str(target / "wheels"),
            "-r",
            str(config.ROOT / "requirements.lock.txt"),
        ],
        check=True,
    )
    (target / "install_offline.py").write_text(INSTALLER, encoding="utf-8")
    (target / "PREREQUISITES.txt").write_text(
        "Windows x64; Python 3.12; compatible NVIDIA driver; FFmpeg and ffprobe on PATH.\n"
        "FFmpeg and the driver are host prerequisites and are not redistributed in this kit.\n"
        "Run python install_offline.py with networking disconnected. From application, run\n"
        ".venv\\Scripts\\python -m scripts.mom start. Create a new local account in the browser.\n"
        "This kit contains no meeting data/accounts. Hashes detect damage, not publisher authenticity.\n",
        encoding="utf-8",
    )
    files = {}
    for file in sorted(target.rglob("*")):
        if file.is_file():
            with file.open("rb") as stream:
                files[file.relative_to(target).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = {
        "version": 1,
        "platform": platform.system(),
        "architecture": platform.machine(),
        "python": list(sys.version_info[:2]),
        "files": files,
        "disconnected_workflow": "not yet verified",
        "target_laptop": "not run",
    }
    (target / "kit.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared offline kit with {len(files)} checksummed files. See PREREQUISITES.txt.")
