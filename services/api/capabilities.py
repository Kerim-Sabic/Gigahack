import importlib.util

from . import config


def capabilities():
    return {
        "parakeet": {
            "available": importlib.util.find_spec("nemo") is not None
            and (config.MODELS / "parakeet/parakeet-tdt-0.6b-v3.nemo").exists(),
            "qualification": "not measured",
            "prerequisite": "Prepare nvidia/parakeet-tdt-0.6b-v3 parakeet-tdt-0.6b-v3.nemo and a compatible isolated NeMo environment",
            "license": "CC-BY-4.0 model; inspect model card before preparation",
        },
        "diarization": {
            "available": importlib.util.find_spec("pyannote") is not None
            and (config.MODELS / "diarization/config.yaml").exists(),
            "qualification": "not measured",
            "prerequisite": "Accept Community-1 access terms; prepare full local assets and pyannote.audio",
            "license": "CC-BY-4.0 model; gated access required",
        },
        "manual_speaker_labels": {"available": True, "qualification": "implemented"},
    }
