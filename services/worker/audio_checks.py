"""Source-clock observations for review; never inferred transcript or speaker truth."""
import math

from services.api.db import transaction


def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return merged


def speech_gaps(turns, segments, samples, minimum_samples=8000):
    """Subtract nonempty transcript spans from diarized speech; overlapping turns count once."""
    speech = merge_intervals((max(0, math.floor(t["start"] * 16000)),
                              min(samples, math.ceil(t["end"] * 16000))) for t in turns)
    covered = merge_intervals((max(0, s["start"]), min(samples, s["end"]))
                              for s in segments if s["text"].strip())
    index = 0
    for start, end in speech:
        while index < len(covered) and covered[index][1] <= start:
            index += 1
        cursor, position = start, index
        while position < len(covered) and covered[position][0] < end:
            left, right = covered[position]
            if left - cursor >= minimum_samples:
                yield {"start": cursor, "end": min(left, end)}
            cursor = max(cursor, right)
            if cursor >= end:
                break
            position += 1
        if end - cursor >= minimum_samples:
            yield {"start": cursor, "end": end}


def save_checks(job, kind, intervals):
    # One short transaction publishes a complete stage's observations; retry is idempotent.
    with transaction() as c:
        c.execute("DELETE FROM audio_checks WHERE job_id=? AND kind=?", (job["id"], kind))
        c.executemany("INSERT INTO audio_checks(job_id,kind,start,end) VALUES(?,?,?,?) ON CONFLICT DO NOTHING",
                      ((job["id"], kind, s["start"], s["end"]) for s in intervals))
