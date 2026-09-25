"""Identity of the local implementation and prepared dependency manifests."""

import hashlib

from . import config


FILES = (
    "services/worker/stage.py",
    "services/worker/reconcile.py",
    "services/worker/optional.py",
    "services/worker/supervisor.py",
    "services/worker/resources.py",
    "services/worker/process_identity.py",
    "services/worker/assets.py",
    "services/api/domain.py",
    "services/api/quantities.py",
    "services/api/dates.py",
    "manifests/models.lock.json",
    "manifests/tools.lock.json",
    "manifests/tool-files.lock.json",
    "requirements.lock.txt",
)


def runtime_identity():
    return {name: hashlib.sha256((config.ROOT / name).read_bytes()).hexdigest() for name in FILES}
