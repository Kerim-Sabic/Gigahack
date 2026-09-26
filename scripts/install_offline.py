"""Standalone standard-library installer; no downloads or existing-install mutation."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import venv
import zipfile
from pathlib import Path, PurePosixPath

RESERVE = 5 * 1024**3


def safe_path(root, name):
    relative = PurePosixPath(name)
    if not name or relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
        raise ValueError("Unsafe package path")
    root = Path(root).resolve()
    path = root.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(root) or any(
        p.is_symlink() for p in [path, *path.parents] if p != root and p.is_relative_to(root)
    ):
        raise ValueError("Package links are not supported")
    return path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "kit.json").read_text(encoding="utf-8"))
    if manifest.get("version") != 2 or manifest.get("kind") != "standalone-core":
        raise ValueError("This installer requires a version-2 standalone core package")
    if (
        manifest["python"] != list(sys.version_info[:2])
        or manifest["platform"] != platform.system()
        or manifest["architecture"].lower() != platform.machine().lower()
    ):
        raise ValueError("Use the recorded Python minor version, operating system and architecture")
    env = root / "application/.venv"
    if env.exists():
        raise ValueError("Environment already exists; use a fresh package directory")
    expected = set(manifest["files"]) | {"kit.json"}
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() or p.is_symlink()}
    if actual != expected:
        raise ValueError("Package contains missing or unlisted files")
    for name, digest in manifest["files"].items():
        path = safe_path(root, name)
        if not path.is_file() or sha(path) != digest:
            raise ValueError("Package checksum mismatch: " + name)
    wheels = list((root / "wheels").glob("*.whl"))
    if not wheels:
        raise ValueError("No prepared wheels")
    unpacked = sum(sum(item.file_size for item in zipfile.ZipFile(p).infolist()) for p in wheels)
    # Existing kit bytes are already allocated. Budget extraction, pip staging and venv overhead.
    additional = unpacked * 2 + 256 * 1024**2
    if shutil.disk_usage(root).free < RESERVE + additional:
        raise OSError("Insufficient installation space; preserve the 5 GiB reserve")
    return manifest, additional


def install(root):
    root = Path(root).resolve()
    _, additional = verify(root)
    print("Verified package; reserved installation headroom:", additional, flush=True)
    env = root / "application/.venv"
    venv.create(env, with_pip=True)
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    staging = root / ".install-temp"
    staging.mkdir()
    environment = dict(
        os.environ,
        PIP_CONFIG_FILE=os.devnull,
        PYTHONNOUSERSITE="1",
        TEMP=str(staging),
        TMP=str(staging),
        TMPDIR=str(staging),
    )
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--disable-pip-version-check",
            "--no-index",
            "--no-cache-dir",
            "--only-binary=:all:",
            "--find-links",
            str(root / "wheels"),
            "-r",
            str(root / "application/requirements.lock.txt"),
        ],
        env=environment,
        check=True,
    )
    print("Offline core installation complete. Follow PREREQUISITES.txt. Optional models are not included.")


if __name__ == "__main__":
    install(Path(__file__).resolve().parent)
