"""Real hard-kill checks, with an unrelated process that must remain alive."""

import json
import subprocess
import sys
import time

import psutil
import pytest

from services.api import config


def alive(process):
    try:
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


@pytest.mark.skipif(sys.platform not in ("win32", "linux"), reason="supported deployment platforms")
def test_hard_stage_death_removes_owned_child_only(tmp_path):
    ready = tmp_path / "ready.json"
    source = """
import json, os, subprocess, sys, time
from pathlib import Path
from services.worker.ownership import contain_windows_children, child_command
contain_windows_children()
child = subprocess.Popen(child_command([sys.executable, '-c',
    'import pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text(\"ready\"); time.sleep(120)',
    sys.argv[1] + '.child']))
while not Path(sys.argv[1] + '.child').exists():
    time.sleep(.02)
Path(sys.argv[1]).write_text(json.dumps({'pid': child.pid}))
time.sleep(120)
"""
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    stage = subprocess.Popen([sys.executable, "-c", source, str(ready)], cwd=config.ROOT)
    child = None
    try:
        deadline = time.monotonic() + 30
        while not ready.exists() and time.monotonic() < deadline and stage.poll() is None:
            time.sleep(.05)
        assert ready.exists(), "owned child did not start"
        child = psutil.Process(json.loads(ready.read_text())["pid"])
        stage.kill()
        stage.wait(10)
        deadline = time.monotonic() + 10
        while alive(child) and time.monotonic() < deadline:
            time.sleep(.05)
        assert not alive(child)
        assert unrelated.poll() is None
    finally:
        for process in (stage, unrelated):
            if process.poll() is None:
                process.kill()
            process.wait(10)
        if child is not None:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass


@pytest.mark.skipif(sys.platform != "linux", reason="Linux parent-death signal")
def test_binding_rejects_parent_that_already_exited():
    result = subprocess.run([sys.executable, "-c",
        "from services.worker.ownership import bind_to_parent; bind_to_parent(-1)"],
        cwd=config.ROOT, capture_output=True)
    assert result.returncode != 0
    assert b"model_parent_gone" in result.stderr
