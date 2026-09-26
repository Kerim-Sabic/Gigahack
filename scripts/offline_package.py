"""Build a fresh, checksummed Windows core kit using ordinary copies only."""

import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from services.api import config
from services.api.storage import require_space
from scripts.install_offline import safe_path, sha


def application_files(root):
    root = Path(root).resolve()
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode("utf-8").split("\0")
    files = {name: safe_path(root, name) for name in tracked if name}
    for path in (root / "apps/web/dist").rglob("*"):
        if path.is_file():
            name = path.relative_to(root).as_posix()
            files[name] = safe_path(root, name)
    if "config/inference.toml" not in files or "apps/web/dist/index.html" not in files:
        raise ValueError("Committed configuration and built frontend are required")
    return files


def reused_wheels(wheelhouse, root):
    wheelhouse = Path(wheelhouse).resolve()
    prior = wheelhouse.parent
    manifest = json.loads((prior / "kit.json").read_text(encoding="utf-8"))
    if (
        manifest["platform"] != platform.system()
        or manifest["python"] != list(sys.version_info[:2])
        or manifest["architecture"].lower() != platform.machine().lower()
    ):
        raise ValueError("Prepared wheels have a different platform/Python/architecture")
    lock = "application/requirements.lock.txt"
    if (
        sha(prior / lock) != manifest["files"][lock]
        or (prior / lock).read_bytes() != (root / "requirements.lock.txt").read_bytes()
    ):
        raise ValueError("Prepared wheel requirements do not match the current lock")
    result = {}
    for name, expected in manifest["files"].items():
        if name.startswith("wheels/") and name.endswith(".whl"):
            source = safe_path(prior, name)
            if sha(source) != expected:
                raise ValueError("Prepared wheel checksum mismatch: " + name)
            result[name] = source
    if not result or {p.name for p in wheelhouse.iterdir()} != {p.name for p in result.values()}:
        raise ValueError("Prepared wheelhouse contains missing or unlisted files")
    return result


def prepare(path, wheelhouse=None):
    from scripts.mom import verify_assets
    import playwright

    if not path:
        raise SystemExit("prepare-offline requires --path to a new directory")
    target = Path(path).resolve()
    if target.exists():
        raise SystemExit("Offline kit destination must not exist; the prior kit is never overwritten")
    if platform.system() != "Windows":
        raise SystemExit(
            "This builder packages Windows core only. Linux/optional distribution remains separate."
        )
    root = config.ROOT
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip():
        raise SystemExit(
            "Commit the reviewed source before packaging; dirty or untracked source is not a release"
        )
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    verify_assets()
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("Node/npm is required on the preparation machine to build the pinned frontend")
    subprocess.run([npm, "run", "build", "--prefix", str(root / "apps/web")], cwd=root, check=True)
    files = {"application/" + name: source for name, source in application_files(root).items()}
    models = json.loads((root / "manifests/models.lock.json").read_text(encoding="utf-8"))
    for group, spec in models.items():
        for name in spec["files"]:
            files["application/models/" + group + "/" + name] = safe_path(config.MODELS, group + "/" + name)
    for name in json.loads((root / "manifests/tool-files.lock.json").read_text(encoding="utf-8"))["Windows"]:
        files["application/.runtime/tools/" + name] = safe_path(root / ".runtime/tools", name)
    browser_root = Path(
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH", Path(os.environ["LOCALAPPDATA"]) / "ms-playwright")
    )
    spec = json.loads(
        (Path(playwright.__file__).parent / "driver/package/browsers.json").read_text(encoding="utf-8")
    )
    for entry in spec["browsers"]:
        if entry["name"] not in ("chromium", "chromium-headless-shell", "ffmpeg", "winldd"):
            continue
        folder = browser_root / f"{entry['name'].replace('-', '_')}-{entry['revision']}"
        if not folder.is_dir():
            raise ValueError("Missing prepared browser component: " + folder.name)
        for source in folder.rglob("*"):
            if source.is_file():
                name = source.relative_to(browser_root).as_posix()
                files["application/.runtime/browsers/" + name] = safe_path(browser_root, name)
    if not wheelhouse:
        raise SystemExit(
            "Use --wheelhouse pointing to a verified prepared kit/wheels; this command never downloads dependencies"
        )
    wheels = reused_wheels(wheelhouse, root)
    files.update(wheels)
    files["install_offline.py"] = root / "scripts/install_offline.py"
    copied_bytes = sum(p.stat().st_size for p in files.values())
    unpacked = sum(sum(x.file_size for x in zipfile.ZipFile(p).infolist()) for p in wheels.values())
    # Include both the complete copy and later install staging, without assuming compression.
    projected = copied_bytes + unpacked * 2 + 256 * 1024**2
    require_space(target, projected)
    print(
        json.dumps(
            {
                "copy_bytes": copied_bytes,
                "installation_headroom_bytes": projected - copied_bytes,
                "reserve_bytes": config.MIN_FREE_BYTES,
                "source_revision": revision,
            }
        ),
        flush=True,
    )
    target.mkdir(parents=True)
    hashes = {}
    for name, source in files.items():
        require_space(target, source.stat().st_size)
        destination = safe_path(target, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        expected = sha(source)
        if sha(destination) != expected:
            raise OSError("Copied file changed or failed integrity verification: " + name)
        hashes[name] = expected
    notice = target / "PREREQUISITES.txt"
    notice.write_text(
        "Windows x64 core standalone package; Python 3.12, NVIDIA driver, FFmpeg/ffprobe on PATH.\n"
        "Contains pinned Whisper/Qwen, native tools, Chromium, compiled UI and offline wheels.\n"
        "Does not include optional Parakeet/Community-1 or their Linux runtime.\n"
        "Run python install_offline.py in this fresh directory, then from application run\n"
        ".venv\\Scripts\\python -m scripts.mom doctor and scripts.mom start.\n"
        "Keep the old installation unchanged. Create a new local account; no meetings/accounts are copied.\n"
        "Hashes detect corruption, not publisher authenticity. Windows egress and target fit remain unverified.\n",
        encoding="utf-8",
    )
    hashes["PREREQUISITES.txt"] = sha(notice)
    manifest = dict(
        version=2,
        kind="standalone-core",
        source_revision=revision,
        platform=platform.system(),
        architecture=platform.machine(),
        python=list(sys.version_info[:2]),
        files=hashes,
        copy_bytes=copied_bytes,
        installation_headroom_bytes=projected - copied_bytes,
        disconnected_workflow="not yet verified for this package",
        target_laptop="not run",
        optional_models="excluded; prepared Linux distribution is separate",
    )
    (target / "kit.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(hashes)} files by ordinary copy. See PREREQUISITES.txt.", flush=True)
