"""Verify prepared native files without downloading or executing them."""

import hashlib
import json
import platform

from services.api import config


def verify_optional_assets(stage, progress=None):
    name = {"parakeet": "parakeet", "diarize": "diarization"}[stage]
    manifest = config.ROOT / "manifests/optional-models.lock.json"
    try:
        files = json.loads(manifest.read_text(encoding="utf-8"))[name]["files"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError("optional_asset_manifest_missing_or_invalid") from error
    required = {"parakeet-tdt-0.6b-v3.nemo"} if stage == "parakeet" else {
        "config.yaml", "embedding/pytorch_model.bin", "segmentation/pytorch_model.bin",
        "plda/plda.npz", "plda/xvec_transform.npz",
    }
    if not isinstance(files, dict) or not required.issubset(files):
        raise RuntimeError("optional_asset_manifest_incomplete")
    root = (config.MODELS / name).resolve()
    if not root.is_relative_to(config.MODELS.resolve()):
        raise RuntimeError("optional_asset_outside_model_directory")
    if progress:
        progress.begin("checking", len(files), "items")
    for index, (filename, expected) in enumerate(files.items(), 1):
        path = root / filename
        if not path.resolve().is_relative_to(root) or not path.is_file():
            raise RuntimeError("optional_asset_missing_or_outside_model_directory")
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise RuntimeError("optional_asset_checksum_mismatch: " + name + "/" + filename)
        if progress:
            progress.advance(index, force=True)


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
