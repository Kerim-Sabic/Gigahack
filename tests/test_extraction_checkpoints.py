import json

import pytest

from services.worker.extraction_checkpoints import ExtractionCheckpoints, digest


SOURCE = {"s": {"id": "s", "revision": 1, "start": 0, "end": 16000,
                "text": "Verificăm cererea сегодня."}}
EVENT = {"subject": "request", "category": "action", "kind": "propose", "text": SOURCE["s"]["text"],
         "evidence": [{"segment_id": "s", "revision": 1, "field": "text", "quote": SOURCE["s"]["text"]}]}


def test_completed_units_survive_restart_and_all_split_events_remain(tmp_path):
    first = ExtractionCheckpoints(tmp_path, {"source": SOURCE, "settings": {"context": 4096}})
    request = {"group": ["s"]}
    # Recursive extraction can return more than the per-response 12-event cap.
    first.save("group", request, [EVENT] * 13, [{"original_model_response": "retained"}], SOURCE)
    restarted = ExtractionCheckpoints(tmp_path, {"source": SOURCE, "settings": {"context": 4096}})
    assert len(restarted.load("group", request, SOURCE)) == 13
    assert restarted.reused == {"group": 1, "event": 0}
    stored = json.loads(first.path("group", request).read_text(encoding="utf-8"))
    assert stored["payload"]["raw_responses"] == [{"original_model_response": "retained"}]
    assert not first.path("event", {"unfinished": True}).exists()


def test_source_config_and_previous_context_changes_invalidate(tmp_path):
    cache = ExtractionCheckpoints(tmp_path, {"source": SOURCE, "settings": 1})
    request = {"event": EVENT, "previous_digest": "original"}
    cache.save("event", request, [EVENT], [], SOURCE)
    assert cache.load("event", {**request, "previous_digest": "changed"}, SOURCE) is None
    assert cache.load("event", request, {"s": {**SOURCE["s"], "revision": 2}}) is None
    assert cache.load("event", request, {"s": {**SOURCE["s"], "text": "Other source"}}) is None
    for changed in ({"source": SOURCE, "settings": 2}, {"source": {}, "settings": 1}):
        assert ExtractionCheckpoints(tmp_path, changed).load("event", request, SOURCE) is None


def test_corruption_and_failed_atomic_write_do_not_publish_partial_work(tmp_path, monkeypatch):
    import services.worker.extraction_checkpoints as module

    cache = ExtractionCheckpoints(tmp_path, {})
    cache.save("event", EVENT, [EVENT], [], SOURCE)
    path = cache.path("event", EVENT)
    original = path.read_bytes()
    stored = json.loads(original)
    stored["payload"]["events"][0]["text"] = "Corrupted"
    path.write_text(json.dumps(stored))
    assert cache.load("event", EVENT, SOURCE) is None
    # Even a correctly checksummed envelope must pass current source validation.
    stored["payload"]["events"][0]["evidence"][0]["quote"] = "Not in source"
    stored["sha256"] = digest(stored["payload"])
    path.write_text(json.dumps(stored))
    assert cache.load("event", EVENT, SOURCE) is None
    path.write_bytes(original)

    def fail(*args):
        raise OSError("simulated full disk")

    monkeypatch.setattr(module, "atomic_write", fail)
    with pytest.raises(OSError, match="full disk"):
        cache.save("event", {"next": True}, [EVENT], [], SOURCE)
    assert cache.load("event", EVENT, SOURCE)
    assert not cache.path("event", {"next": True}).exists()


def test_invalid_work_is_not_checkpointed(tmp_path):
    cache = ExtractionCheckpoints(tmp_path, {})
    with pytest.raises(ValueError):
        cache.save("event", {}, [{**EVENT, "kind": "approved_by_app"}], [], SOURCE)
    assert not list(cache.folder.glob("*.json"))


def test_raw_journal_disk_failure_reaps_started_model(tmp_path, monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    import httpx
    from services.worker import stage
    from services.api import provenance

    llm = stage.load_settings().llm
    model_dir = tmp_path / "models" / llm.model_directory
    model_dir.mkdir(parents=True)
    (model_dir / llm.model_file).write_bytes(b"explicit fake model")
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests/models.lock.json").write_text(json.dumps({llm.model_directory: {"files": {llm.model_file: "synthetic"}}}))
    exe = tmp_path / "server"
    exe.write_bytes(b"explicit fake server")
    monkeypatch.setenv("MOM_LLAMA_SERVER", str(exe))
    monkeypatch.setattr(stage, "ROOT", tmp_path)
    monkeypatch.setattr(stage, "MODELS", tmp_path / "models")
    monkeypatch.setattr(provenance, "runtime_identity", lambda: {"code": "synthetic"})
    calls = []
    process = SimpleNamespace(terminate=lambda: calls.append("terminate"), wait=lambda *_: calls.append("wait"))
    monkeypatch.setattr(stage.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: SimpleNamespace(close=lambda: calls.append("close")))

    def fail(*args, **kwargs):
        raise OSError("simulated journal disk failure")

    monkeypatch.setattr(Path, "touch", fail)
    with pytest.raises(OSError, match="journal disk failure"):
        stage.extract({"run_dir": str(tmp_path), "segments": list(SOURCE.values()),
                       "meeting": {"date": "", "timezone": ""}, "config": {"device": "cpu"}})
    assert calls == ["close", "terminate", "wait"]
