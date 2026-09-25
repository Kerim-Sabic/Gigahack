"""Storage admission checks; no deletion of user data to make room."""
import errno
import shutil
from pathlib import Path

from . import config


def require_space(path, additional=0):
    target = Path(path).resolve()
    while not target.exists():
        target = target.parent
    if additional < 0 or shutil.disk_usage(target).free < config.MIN_FREE_BYTES + additional:
        raise OSError(errno.ENOSPC, "storage_low")
