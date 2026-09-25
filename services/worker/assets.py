"""Verify prepared native files without downloading or executing them."""

import hashlib
import json
import platform

from services.api import config


def verify_tools():
    manifest = config.ROOT / "manifests/tool-files.lock.json"
    if not manifest.is_file():
        raise SystemExit("Native file manifest missing; run prepare-tools during online preparation.")
    files = json.loads(manifest.read_text(encoding="utf-8")).get(platform.system(), {})
    if not files or not all(
        any(name.startswith(tool + "/") for name in files) for tool in ("llama", "mailpit")
    ):
        raise SystemExit("Native tool files are not pinned for this platform; run prepare-tools.")
    root = config.ROOT / ".runtime/tools"
    for name, expected in files.items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise SystemExit("Prepared native tool file missing or outside tool directory: " + name)
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise SystemExit("Native tool checksum mismatch: " + name)
