import hashlib
import json

import pytest

from services.api import config
from services.worker.assets import verify_optional_assets


def prepare(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "MODELS", tmp_path / "models")
    (tmp_path / "manifests").mkdir()
    model = tmp_path / "models/parakeet/parakeet-tdt-0.6b-v3.nemo"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"synthetic pinned bytes; never executed")
    manifest = tmp_path / "manifests/optional-models.lock.json"
    data = {"parakeet": {"files": {model.name: hashlib.sha256(model.read_bytes()).hexdigest()}}}
    manifest.write_text(json.dumps(data))
    return model, manifest, data


def test_optional_model_tamper_and_missing_assets_fail_locally(tmp_path, monkeypatch):
    model, manifest, data = prepare(tmp_path, monkeypatch)
    verify_optional_assets("parakeet")
    model.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="checksum_mismatch"):
        verify_optional_assets("parakeet")
    model.unlink()
    with pytest.raises(RuntimeError, match="missing_or_outside"):
        verify_optional_assets("parakeet")
    manifest.write_text(json.dumps({"parakeet": {"files": {}}}))
    with pytest.raises(RuntimeError, match="manifest_incomplete"):
        verify_optional_assets("parakeet")


def test_optional_manifest_cannot_escape_prepared_directory(tmp_path, monkeypatch):
    model, manifest, data = prepare(tmp_path, monkeypatch)
    outside = tmp_path / "outside"
    outside.write_bytes(b"not a model asset")
    data["parakeet"]["files"]["../../outside"] = hashlib.sha256(outside.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(data))
    with pytest.raises(RuntimeError, match="missing_or_outside"):
        verify_optional_assets("parakeet")
