"""Local-only optional runtime registration; no downloads or inference imports."""

import hashlib
import json
from pathlib import Path
import sys

from services.api import config
from services.api.audio import atomic_write
from services.worker.assets import verify_optional_assets
from services.worker.optional_runtime import verify_runtime


def main():
    report = verify_runtime()
    for stage in ("parakeet", "diarize"):
        verify_optional_assets(stage)
    report["models_manifest_sha256"] = hashlib.sha256(
        (config.ROOT / "manifests/optional-models.lock.json").read_bytes()).hexdigest()
    report["qualification"] = "Prerequisites verified locally; accuracy and target hardware not qualified"
    atomic_write(Path(sys.prefix) / "secure-mom-runtime.json", json.dumps(report, indent=2).encode())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
