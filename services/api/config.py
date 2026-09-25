import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("MOM_DATA", ROOT / ".runtime"))
MODELS = Path(os.environ.get("MOM_MODELS", ROOT / "models"))
ORIGIN = os.environ.get("MOM_ORIGIN", "http://127.0.0.1:8765")
MAX_BYTES = 1024**3
MAX_SECONDS = 7200
if (ROOT / ".runtime/browsers").is_dir():
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".runtime/browsers"))


def init_dirs():
    for sub in ["audio", "jobs", "exports", "proofs"]:
        (DATA / sub).mkdir(parents=True, exist_ok=True)
