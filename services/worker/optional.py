import re
import subprocess

from services.api import config
from services.api.db import canonical, transaction


def optional_stages(job, spec, asset, segments, run_stage):
    if spec["config"].get("parakeet"):
        budget, used, clips = int(asset["samples"] * 0.15), 0, []
        for s in segments:
            if not re.search(r"\d|\b(?:not|no|nu|не)\b", s["text"], re.I):
                continue
            start, end = max(0, s["start"] - 3200), min(asset["samples"], s["end"] + 3200)
            if used + end - start > budget:
                continue
            clip = config.DATA / "jobs" / job["id"] / (s["id"] + ".wav")
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    asset["path"],
                    "-ss",
                    str(start / 16000),
                    "-t",
                    str((end - start) / 16000),
                    str(clip),
                ],
                capture_output=True,
                check=True,
                timeout=60,
            )
            clips.append({"segment_id": s["id"], "path": str(clip), "start": start, "end": end})
            used += end - start
        if clips:
            alternatives = run_stage(job, "parakeet", {**spec, "clips": clips})
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
