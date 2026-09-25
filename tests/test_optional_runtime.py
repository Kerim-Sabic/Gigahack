import hashlib
import json
from types import SimpleNamespace

import pytest

from services.worker import optional_runtime as runtime


def test_unreviewed_packages_and_replaced_patches_block_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime.config, "ROOT", tmp_path)
    monkeypatch.setattr(runtime.sys, "platform", "linux")
    monkeypatch.setattr(runtime.sys, "version_info", (3, 12, 0))
    monkeypatch.setattr(runtime.sys, "prefix", str(tmp_path / "env"))
    monkeypatch.setattr(runtime.platform, "machine", lambda: "x86_64")
    folder = tmp_path / "manifests/optional-runtime-experiment"
    folder.mkdir(parents=True)
    manifest = {"packages": [{"name": "Example_Model", "version": "1.0"}], "bootstrap": "pip==26.2.1"}
    (folder.parent / "optional-runtime-candidate.json").write_text(json.dumps(manifest))
    (folder.parent / "optional-runtime-candidate.lock.txt").write_text("synthetic test pins")
    patch = tmp_path / "env/example/patch.py"
    patch.parent.mkdir(parents=True)
    patch.write_bytes(b"verified compatibility change")
    (folder / "patches.json").write_text(json.dumps([{"package": "example-model", "relative_path": "example/patch.py",
        "after": hashlib.sha256(patch.read_bytes()).hexdigest()}]))
    distributions = [SimpleNamespace(metadata={"Name": "example-model"}, version="1.0"),
                     SimpleNamespace(metadata={"Name": "pip"}, version="26.2.1")]
    monkeypatch.setattr(runtime.metadata, "distributions", lambda: distributions)
    monkeypatch.setattr(runtime.metadata, "distribution", lambda _: SimpleNamespace(locate_file=lambda name: tmp_path / "env" / name))
    assert runtime.verify_runtime()["package_count"] == 2
    distributions.append(SimpleNamespace(metadata={"Name": "unreviewed"}, version="1"))
    with pytest.raises(RuntimeError, match="package_mismatch: unreviewed"):
        runtime.verify_runtime()
    distributions.pop()
    patch.write_bytes(b"upstream reinstall removed the fix")
    with pytest.raises(RuntimeError, match="patch_mismatch"):
        runtime.verify_runtime()


@pytest.mark.parametrize("damage", ["fingerprint", "model_manifest", "python", "malformed"])
def test_readiness_rejects_stale_or_incomplete_registration(tmp_path, monkeypatch, damage):
    monkeypatch.setattr(runtime.config, "ROOT", tmp_path)
    monkeypatch.setattr(runtime.sys, "platform", "linux")
    monkeypatch.setattr(runtime, "fingerprint", lambda: "current")
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    models = manifests / "optional-models.lock.json"
    models.write_bytes(b"pinned model hashes")
    prefix = tmp_path / "env"
    (prefix / "bin").mkdir(parents=True)
    python = prefix / "bin/python"
    python.write_bytes(b"test-only executable marker")
    report = {"prefix": str(prefix), "platform": "linux", "fingerprint": "current",
              "models_manifest_sha256": hashlib.sha256(models.read_bytes()).hexdigest()}
    marker = prefix / "secure-mom-runtime.json"
    marker.write_text(json.dumps(report), encoding="utf-8")
    assert runtime.stage_python(str(prefix)) == str(python)
    if damage == "fingerprint":
        report["fingerprint"] = "old"
        marker.write_text(json.dumps(report), encoding="utf-8")
    elif damage == "model_manifest":
        models.write_bytes(b"different model hashes")
    elif damage == "python":
        python.unlink()
    else:
        marker.write_text("[]", encoding="utf-8")
    assert runtime.prepared_runtime(str(prefix)) is None
    with pytest.raises(RuntimeError, match="not_prepared"):
        runtime.stage_python(str(prefix))


def test_optional_runtime_selection_is_frozen_at_queue_time(monkeypatch):
    from services.worker.settings import load_settings, settings_for

    monkeypatch.setenv("MOM_OPTIONAL_RUNTIME", "/prepared/first")
    frozen = load_settings().model_dump()
    monkeypatch.setenv("MOM_OPTIONAL_RUNTIME", "/prepared/second")
    assert load_settings().optional.runtime_prefix == "/prepared/second"
    assert settings_for({"config": {"inference": frozen}}).optional.runtime_prefix == "/prepared/first"


def test_capabilities_require_registration_and_complete_contained_assets(tmp_path, monkeypatch):
    from services.api import capabilities as module
    from services.worker.settings import load_settings

    monkeypatch.setattr(module.config, "ROOT", tmp_path)
    monkeypatch.setattr(module.config, "MODELS", tmp_path / "models")
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    data = {name: {"files": {"weights": "unused-test-hash"}} for name in ("parakeet", "diarization")}
    (manifests / "optional-models.lock.json").write_text(json.dumps(data), encoding="utf-8")
    for name in data:
        folder = tmp_path / "models" / name
        folder.mkdir(parents=True)
        (folder / "weights").write_bytes(b"test asset presence only")
    profile = load_settings().model_dump()
    monkeypatch.setattr(module, "prepared_runtime", lambda _: None)
    assert not module.capabilities(profile)["parakeet"]["available"]
    monkeypatch.setattr(module, "prepared_runtime", lambda _: {"verified": True})
    assert module.capabilities(profile)["parakeet"]["available"]
    (tmp_path / "models/parakeet/weights").unlink()
    assert not module.capabilities(profile)["parakeet"]["available"]
    assert module.capabilities(profile)["diarization"]["available"]
    data["diarization"]["files"] = {"../outside": "unused"}
    (tmp_path / "models/outside").write_bytes(b"not in model directory")
    (manifests / "optional-models.lock.json").write_text(json.dumps(data), encoding="utf-8")
    assert not module.capabilities(profile)["diarization"]["available"]
