import subprocess
import sys

import pytest

from services.api import config
from services.api.db import migrate, transaction
from services.worker import supervisor


def test_oom_retries_once_with_smaller_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DATA", tmp_path)
    migrate()
    calls = []

    def run(job, stage, spec):
        calls.append(spec)
        if len(calls) == 1:
            raise RuntimeError("whisper_oom")
        return {"segments": []}

    monkeypatch.setattr(supervisor, "run_stage", run)
    # No DB row is required for the diagnostic UPDATE.
    assert supervisor.retry_stage({"id": "missing"}, "whisper", {"config": {"device": "cuda"}}) == {
        "segments": []
    }
    assert len(calls) == 2 and calls[1]["config"]["oom_retry"] is True


def test_stage_cancel_terminates_actual_child_process(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    migrate()
    with transaction() as c:
        c.execute(
            "INSERT INTO meetings VALUES('m','synthetic','2026-09-25','Europe/Chisinau','en','Administrative',1,'queued',0)"
        )
        c.execute(
            "INSERT INTO jobs(id,meeting_id,state,stage,cancel,config,created) VALUES('j','m','running','whisper',1,'{}',0)"
        )
    real_popen = subprocess.Popen
    processes = []

    def popen(*args, **kwargs):
        p = real_popen([sys.executable, "-c", "import time; time.sleep(120)"], **kwargs)
        processes.append(p)
        return p

    from services.worker import resources

    monkeypatch.setattr(resources, "query_gpu", lambda: {"devices": {}, "processes": [], "errors": []})
    monkeypatch.setattr(supervisor.subprocess, "Popen", popen)
    with pytest.raises(RuntimeError, match="cancelled"):
        supervisor.run_stage({"id": "j", "meeting_id": "m"}, "whisper", {"config": {"device": "cpu"}})
    assert processes[0].poll() is not None


def test_lease_recovery_preserves_job_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    migrate()
    with transaction() as c:
        c.execute(
            "INSERT INTO meetings VALUES('m','synthetic','2026-09-25','Europe/Chisinau','en','Administrative',1,'queued',0)"
        )
        c.execute(
            "INSERT INTO jobs(id,meeting_id,state,stage,lease,config,created) VALUES('j','m','running','whisper',0,'{}',0)"
        )
    seen = []

    def process(job):
        seen.append(job["id"])
        with transaction() as c:
            c.execute("UPDATE jobs SET state='complete' WHERE id=?", (job["id"],))

    monkeypatch.setattr(supervisor, "process", process)
    assert supervisor.tick()
    assert seen == ["j"]
    with transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1


def test_disk_failure_never_acknowledges_audio(tmp_path, monkeypatch):
    from services.api.audio import atomic_write

    monkeypatch.setattr(
        "services.api.audio.os.fsync", lambda _: (_ for _ in ()).throw(OSError("disk failure"))
    )
    target = tmp_path / "chunk.pcm"
    with pytest.raises(OSError):
        atomic_write(target, b"synthetic")
    assert not target.exists()
