"""Bounded source-linked hypotheses for suspected transcript gaps; no transcript fusion."""
import hashlib
import json
from pathlib import Path

from services.api.audio import atomic_write, canonical_clip, sha
from services.api.db import canonical
from services.api.provenance import runtime_identity
from services.api.storage import require_space


RATE = 16000


def windows(start, end, samples, seconds, padding_seconds):
    if not 0 <= start < end <= samples:
        raise ValueError("invalid_recovery_interval")
    step, padding = seconds * RATE, padding_seconds * RATE
    for left in range(start, end, step):
        right = min(end, left + step)
        yield {"primary_start": left, "primary_end": right,
               "source_start": max(0, left - padding), "source_end": min(samples, right + padding)}


def recover_gaps(model, spec, settings, progress):
    gaps = spec.get("recovery_gaps", [])
    if not gaps:
        return []
    source, samples = spec["audio"], spec["audio_samples"]
    identity = {"audio": sha(Path(source)), "settings": settings.model_dump(),
                "implementation": runtime_identity(), "device": spec["config"]["device"],
                "oom_retry": spec["config"].get("oom_retry", False)}
    key = hashlib.sha256(canonical(identity).encode()).hexdigest()
    directory = Path(spec["run_dir"]) / "gap-recovery" / key
    directory.mkdir(parents=True, exist_ok=True)
    results = []
    # Each completed gap includes its bounded retries; no invented whole-job ETA.
    progress.begin("checking", len(gaps), "items")

    def recognize(gap, span, attempt):
        ident = f'{gap["start"]}-{gap["end"]}-{span["primary_start"]}-{span["primary_end"]}-{attempt}'
        target = directory / (ident + ".json")
        if target.is_file():
            try:
                stored = json.loads(target.read_text(encoding="utf-8"))
                item = stored["payload"]
                if (stored["sha256"] == hashlib.sha256(canonical(item).encode()).hexdigest()
                        and item["identity"] == key and item["span"] == span
                        and item["gap"] == gap and item["attempt"] == attempt):
                    return item
            except (OSError, ValueError, KeyError, TypeError):
                pass
        audio = directory / (ident + ".wav")
        require_space(directory, (span["source_end"] - span["source_start"]) * 2 + 44)
        canonical_clip(source, audio, span["source_start"], span["source_end"])
        try:
            hypotheses = model.transcribe([str(audio)], batch_size=1, timestamps=True)
            if len(hypotheses) != 1:
                raise ValueError("recovery_hypothesis_count_mismatch")
            hypothesis = hypotheses[0]
            item = {"identity": key, "gap": gap, "span": span, "attempt": attempt,
                    "text": hypothesis.text, "timestamps": hypothesis.timestamp}
            raw = canonical(item)
            atomic_write(target, canonical({"payload": item, "sha256": hashlib.sha256(raw.encode()).hexdigest()}).encode())
            return item
        finally:
            # Only this function's bounded derived clip, never the immutable source.
            audio.unlink(missing_ok=True)

    for index, gap in enumerate(gaps):
        for span in windows(gap["start"], gap["end"], samples,
                            settings.recovery_window_seconds, settings.recovery_padding_seconds):
            item = recognize(gap, span, "initial")
            results.append(item)
            # Empty short clips are not retried unchanged or indefinitely.
            if (not item["text"].strip()
                    and span["primary_end"] - span["primary_start"] > settings.recovery_retry_seconds * RATE):
                for retry in windows(span["primary_start"], span["primary_end"], samples,
                                     settings.recovery_retry_seconds, settings.recovery_padding_seconds):
                    results.append(recognize(gap, retry, "short_retry"))
        progress.advance(index + 1)
    return results
