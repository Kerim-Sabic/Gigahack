"""Identity of the local implementation and prepared dependency manifests."""

import hashlib

from . import config


FILES = (
    "config/inference.toml",
    "services/worker/settings.py",
    "services/worker/asr_chunks.py",
    "services/worker/extraction_checkpoints.py",
    "services/api/progress.py",
    "services/api/transcript_state.py",
    "services/api/audio.py",
    "services/api/pcm.py",
    "services/worker/stage.py",
    "services/worker/reconcile.py",
    "services/worker/optional.py",
    "services/worker/audio_checks.py",
    "services/worker/gap_recovery.py",
    "services/worker/optional_runtime.py",
    "services/worker/supervisor.py",
    "services/worker/resources.py",
    "services/worker/process_identity.py",
    "services/worker/ownership.py",
    "services/worker/assets.py",
    "services/api/domain.py",
    "services/api/quantities.py",
    "services/api/dates.py",
    "manifests/models.lock.json",
    "manifests/optional-models.lock.json",
    "manifests/optional-runtime-candidate.json",
    "manifests/optional-runtime-candidate.lock.txt",
    "manifests/optional-runtime-experiment/patches.json",
    "manifests/tools.lock.json",
    "manifests/tool-files.lock.json",
    "requirements.lock.txt",
)


def runtime_identity():
    return {name: hashlib.sha256((config.ROOT / name).read_bytes()).hexdigest() for name in FILES}
