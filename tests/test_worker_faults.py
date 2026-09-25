import subprocess
import sys

import pytest

from services.api import config
from services.api.db import migrate, transaction
from services.worker import supervisor


def test_long_active_stages_survive_and_timestamp_only_heartbeats_do_not():
    clock = [0.0]
    activity = supervisor.StageActivity(1800, clock=lambda: clock[0])
    for minute in range(180):
        clock[0] = minute * 60
        assert not activity.observe({'phase': 'transcribing', 'completed': minute, 'total': 500}, 1)
    # Three hours of genuine work is allowed; changing only a wall-clock heartbeat is not work.
    clock[0] += 1801
    assert activity.observe({'phase': 'transcribing', 'completed': 179, 'total': 500, 'updated_at': 999999}, 1)


def test_active_cpu_keeps_work_alive_when_progress_file_is_unavailable():
    clock = [0.0]
    activity = supervisor.StageActivity(60, clock=lambda: clock[0])
    for second in range(300):
        clock[0] = second
        assert not activity.observe(None, second * 0.02)
    clock[0] += 61
    assert activity.observe(None, 299 * 0.02)


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


def test_failed_decode_publication_does_not_replace_completed_audio(tmp_path, monkeypatch):
    import wave
    from services.api import audio
    source, target = tmp_path / 'original.wav', tmp_path / 'source.wav'
    with wave.open(str(source), 'wb') as output:
        output.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        output.writeframes(b'\0\0' * 32000)
    target.write_bytes(b'previously completed artifact')
    monkeypatch.setattr(audio.os, 'fsync', lambda _: (_ for _ in ()).throw(OSError('synthetic persistence failure')))
    with pytest.raises(OSError):
        audio.decode(source, target)
    assert target.read_bytes() == b'previously completed artifact'
    assert source.exists()
