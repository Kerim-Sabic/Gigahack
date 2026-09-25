import errno
import subprocess
import sys

import pytest

from services.api import audio


def test_storage_failure_reaps_decoder_and_keeps_completed_target(tmp_path, monkeypatch):
    processes = []
    real_popen = subprocess.Popen

    def popen(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(audio.subprocess, "Popen", popen)
    monkeypatch.setattr(audio, "require_space", lambda _: (_ for _ in ()).throw(OSError(errno.ENOSPC, "storage_low")))
    target = tmp_path / "completed.wav"
    target.write_bytes(b"previous completed artifact")
    with pytest.raises(OSError, match="storage_low"):
        audio.run_decoder([sys.executable, "-c", "import time; time.sleep(120)"], target)
    assert processes[0].poll() is not None
    assert target.read_bytes() == b"previous completed artifact"


def test_inactive_decoder_is_stopped(tmp_path, monkeypatch):
    monkeypatch.setattr(audio.config, "DECODE_IDLE_SECONDS", 0.2)
    with pytest.raises(TimeoutError, match="audio_decode_stalled"):
        audio.run_decoder([sys.executable, "-c", "import time; time.sleep(120)"], tmp_path / "partial.wav")
