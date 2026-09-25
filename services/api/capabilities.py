import json

from . import config
from services.worker.optional_runtime import prepared_runtime
from services.worker.settings import load_settings


def capabilities(inference=None):
    settings = inference or load_settings().model_dump()
    ready = prepared_runtime(settings["optional"]["runtime_prefix"]) is not None

    def assets_present(name):
        try:
            files = json.loads((config.ROOT / "manifests/optional-models.lock.json").read_text(encoding="utf-8"))[name]["files"]
            root = (config.MODELS / name).resolve()
            return bool(files) and root.is_relative_to(config.MODELS.resolve()) and all(
                (root / path).resolve().is_relative_to(root) and (root / path).is_file() for path in files)
        except (OSError, ValueError, KeyError, TypeError):
            return False

    return {
        "parakeet": {
            "available": ready and assets_present("parakeet"),
            "qualification": "Experimental comparison; accuracy and target hardware remain unqualified",
            "prerequisite": "Prepare and verify the pinned optional environment, then run the app in Linux/WSL with MOM_OPTIONAL_RUNTIME set",
            "license": "CC-BY-4.0 model; inspect model card before preparation",
        },
        "diarization": {
            "available": ready and assets_present("diarization"),
            "qualification": "Experimental speaker clusters; identities and accuracy require review",
            "prerequisite": "Prepare Community-1 assets and verify the pinned Linux/WSL optional environment",
            "license": "CC-BY-4.0 model; gated access required",
        },
        "manual_speaker_labels": {"available": True, "qualification": "implemented"},
    }
