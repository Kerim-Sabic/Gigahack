"""PID-reuse checks independent of Linux wall-clock/boot-time corrections."""

from pathlib import Path
import sys

import psutil


def identity(pid):
    if sys.platform == "linux":
        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
        except FileNotFoundError:
            raise psutil.NoSuchProcess(pid) from None
        # comm can itself contain spaces and parentheses; fields after it start at state (3).
        fields = stat.rsplit(") ", 1)[1].split()
        return {"kind": "linux_start_ticks", "value": fields[19]}
    return {"kind": "creation_time", "value": psutil.Process(pid).create_time()}


def matches(record):
    if "identity" in record:
        return identity(record["pid"]) == record["identity"]
    return abs(psutil.Process(record["pid"]).create_time() - record["created"]) < 0.01
