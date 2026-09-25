import os
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("MOM_DATA", ROOT / ".runtime"))
MODELS = Path(os.environ.get("MOM_MODELS", ROOT / "models"))
ORIGIN = os.environ.get("MOM_ORIGIN", "http://127.0.0.1:8765")
# Zero disables an operator-imposed cap; available storage is still checked.
MAX_BYTES = int(os.environ.get("MOM_MAX_UPLOAD_BYTES", "0"))
MAX_SECONDS = float(os.environ.get("MOM_MAX_AUDIO_SECONDS", "0"))
MIN_FREE_BYTES = int(os.environ.get("MOM_MIN_FREE_BYTES", str(5 * 1024**3)))
DECODE_IDLE_SECONDS = float(os.environ.get("MOM_DECODE_IDLE_SECONDS", "300"))
if MAX_BYTES < 0 or not math.isfinite(MAX_SECONDS) or MAX_SECONDS < 0 or MIN_FREE_BYTES < 5 * 1024**3 or not math.isfinite(DECODE_IDLE_SECONDS) or DECODE_IDLE_SECONDS < 30:
    raise ValueError("invalid_audio_resource_policy")
if (ROOT / ".runtime/browsers").is_dir():
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".runtime/browsers"))


def init_dirs():
    for sub in ["audio", "jobs", "exports", "proofs"]:
        (DATA / sub).mkdir(parents=True, exist_ok=True)
