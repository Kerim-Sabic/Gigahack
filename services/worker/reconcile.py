"""Bounded retrieval of source turns and prior topic candidates for model review.

Retrieval proposes context only. Word similarity never authorizes a subject merge.
"""

import json
import re


def context_for(event, segments, previous, token_count, budget=1800):
    by_id = {s["id"]: s for s in segments}
    positions = {s["id"]: i for i, s in enumerate(segments)}
    required = set(e["segment_id"] for e in event["evidence"])
    if not required <= by_id.keys():
        raise ValueError("source_revision_mismatch")
    near = set()
    for ident in required:
        index = positions[ident]
        near.update(s["id"] for s in segments[max(0, index - 2) : index + 1])
    words = set(re.findall(r"[^\W\d_]+", event["subject"].casefold()))
    latest = {}
    for prior in previous:
        latest[prior["subject"]] = prior
    ranked = sorted(
        latest.values(),
        key=lambda e: (
            len(words & set(re.findall(r"[^\W\d_]+", e["subject"].casefold()))),
            previous.index(e),
        ),
        reverse=True,
    )
    candidates = ranked[:4]

    def payload():
        source_ids = required | near | {r["segment_id"] for e in candidates for r in e["evidence"]}
        return {
            # Extraction paraphrases can lose a hedge or question. Do not prime the
            # independent speech-act review with that text or inferred field changes.
            "candidate": {
                k: event.get(k)
                for k in (
                    "subject",
                    "evidence",
                )
            },
            "earlier_topic_candidates": [
                {
                    k: e.get(k)
                    for k in (
                        "subject",
                        "text",
                        "kind",
                        "category",
                        "owner",
                        "raw_due",
                        "condition",
                        "value",
                        "changed_fields",
                    )
                }
                for e in candidates
            ],
            "source": [s for s in segments if s["id"] in source_ids],
        }

    while True:
        result = payload()
        if token_count(json.dumps(result, ensure_ascii=False)) <= budget:
            return result
        if candidates:
            candidates.pop()
        elif near - required:
            near.remove(
                max(
                    near - required,
                    key=lambda ident: min(abs(positions[ident] - positions[r]) for r in required),
                )
            )
        else:
            raise RuntimeError("reconciliation_source_exceeds_context")
