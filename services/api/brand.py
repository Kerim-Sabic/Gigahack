"""Display identity only; never changes stored IDs or operational configuration."""
import json

from .config import ROOT

NAME = json.loads((ROOT / "config/brand.json").read_text(encoding="utf-8"))["name"]
