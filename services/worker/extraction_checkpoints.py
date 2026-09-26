"""Atomic validated work units; checkpoints never authorize review or publication."""
import hashlib
import json
from pathlib import Path

from services.api.audio import atomic_write
from services.api.db import canonical
from services.api.domain import Candidate, validate_evidence
from services.api.storage import require_space


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class ExtractionCheckpoints:
    def __init__(self, run_dir, identity):
        self.identity = digest(identity)
        self.folder = Path(run_dir) / "extraction-checkpoints" / self.identity
        self.folder.mkdir(parents=True, exist_ok=True)
        self.reused = {"group": 0, "event": 0}

    def path(self, phase, request):
        if phase not in self.reused:
            raise ValueError("invalid_checkpoint_phase")
        return self.folder / (phase + "-" + digest(request) + ".json")

    def load(self, phase, request, sources):
        path = self.path(phase, request)
        try:
            # A corrupt local file must not allocate unbounded memory on recovery.
            if path.stat().st_size > 32 * 1024**2:
                return None
            stored = json.loads(path.read_text(encoding="utf-8"))
            payload = stored["payload"]
            if (stored["sha256"] != digest(payload) or payload["identity"] != self.identity
                    or payload["request"] != digest(request) or payload["phase"] != phase):
                return None
            events = [Candidate.model_validate(event) for event in payload["events"]]
            for event in events:
                validate_evidence(event, sources)
            if phase == "event" and len(events) != 1:
                return None
            self.reused[phase] += 1
            return [event.model_dump() for event in events]
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def save(self, phase, request, events, responses, sources):
        validated = [Candidate.model_validate(event) for event in events]
        for event in validated:
            validate_evidence(event, sources)
        if phase == "event" and len(validated) != 1:
            raise ValueError("event_checkpoint_requires_one_event")
        payload = {"identity": self.identity, "request": digest(request), "phase": phase,
                   "events": [event.model_dump() for event in validated], "raw_responses": responses}
        serialized = canonical({"payload": payload, "sha256": digest(payload)}).encode("utf-8")
        # Oversize diagnostic responses still survive in the raw journal. Do not truncate
        # source or results just to checkpoint them; such a unit will recompute on retry.
        if len(serialized) > 32 * 1024**2:
            return
        require_space(self.folder, len(serialized))
        atomic_write(self.path(phase, request), serialized)
