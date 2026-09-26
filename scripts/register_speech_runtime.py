"""Register the current isolated runtime against repository-pinned dependencies."""

import argparse
import json
import sys
from pathlib import Path

from services.api.audio import atomic_write
from services.speech.runtime import fingerprint, verify_runtime


def register(name):
    if sys.platform != 'linux' or sys.prefix == sys.base_prefix:
        raise RuntimeError('run_with_the_prepared_linux_virtual_environment_python')
    marker = Path(sys.prefix)/'notavra-speech-runtime.json'
    previous = marker.read_bytes() if marker.exists() else None
    value = {'runtime': name, 'prefix': str(Path(sys.prefix).resolve()), 'fingerprint': fingerprint(name)}
    try:
        atomic_write(marker, json.dumps(value).encode())
        result = verify_runtime(name)  # Exact package set and direct source revisions.
    except BaseException:
        if previous is None:
            marker.unlink(missing_ok=True)
        else:
            atomic_write(marker, previous)
        raise
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', choices=['qwen-original', 'nemotron3', 'vibevoice'], required=True)
    register(parser.parse_args().name)
