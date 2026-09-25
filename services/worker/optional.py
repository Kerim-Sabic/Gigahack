from services.api import config
from services.api.audio import canonical_clip
from services.api.db import canonical, transaction
from .audio_checks import save_checks, speech_gaps


def optional_stages(job, spec, asset, segments, run_stage):
    from .settings import settings_for

    settings = settings_for(spec).optional
    if spec["config"].get("parakeet"):
        budget, used, clips = int(asset["samples"] * settings.parakeet_audio_fraction), 0, []
        for s in segments:
            start, end = max(0, s["start"] - 3200), min(asset["samples"], s["end"] + 3200)
            if settings.parakeet_audio_fraction < 1 and used + end - start > budget:
                continue
            clip = config.DATA / "jobs" / job["id"] / (s["id"] + ".wav")
            canonical_clip(asset["path"], clip, start, end)
            clips.append({"segment_id": s["id"], "path": str(clip), "start": start, "end": end})
            used += end - start
        if clips:
            alternatives = run_stage(job, "parakeet", {**spec, "clips": clips})
            empty_ids = {h["segment_id"] for h in alternatives["hypotheses"] if not h["text"].strip()}
            save_checks(job, "empty_second_recognizer", [s for s in segments if s["id"] in empty_ids])
            with transaction() as c:
                for h in alternatives["hypotheses"]:
                    c.execute(
                        "UPDATE segments SET alternatives=? WHERE id=? AND meeting_id=?",
                        (
                            canonical(
                                [
                                    {
                                        "engine": "parakeet",
                                        "text": h["text"],
                                        "source_start": h["source_start"],
                                        "timestamps": h["timestamps"],
                                        "review": "unreviewed",
                                    }
                                ]
                            ),
                            h["segment_id"],
                            job["meeting_id"],
                        ),
                    )
    if spec["config"].get("diarization"):
        diarization = run_stage(job, "diarize", spec)
        save_checks(job, "speech_without_transcript", speech_gaps(diarization["turns"], segments, asset["samples"]))
        with transaction() as c:
            for s in segments:
                overlapping = [
                    t
                    for t in diarization["turns"]
                    if t["start"] * 16000 < s["end"] and t["end"] * 16000 > s["start"]
                ]
                labels = {t["cluster"] for t in overlapping}
                label = next(iter(labels)) if len(labels) == 1 else "Unknown / overlapping speakers"
                c.execute("UPDATE segments SET speaker=? WHERE id=? AND speaker IS NULL", (label, s["id"]))
