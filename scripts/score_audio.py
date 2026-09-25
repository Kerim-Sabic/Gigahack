"""Score an observed ASR JSON file against separately supplied reference annotations."""

import argparse
import hashlib
import json
from pathlib import Path

from scripts.audio_metrics import score


def build_report(reference_path, observed_path):
    reference_bytes = reference_path.read_bytes()
    observed_bytes = observed_path.read_bytes()
    reference = json.loads(reference_bytes)
    observed = json.loads(observed_bytes)
    if not isinstance(reference.get("provenance"), dict) or not reference["provenance"].get("review_status"):
        raise ValueError("reference_provenance_and_review_status_required")
    segments = observed["segments"]
    if not isinstance(segments, list) or any(not isinstance(s.get("text"), str) for s in segments):
        raise ValueError("observed_segments_required")
    report = score(reference["reference_text"], " ".join(s["text"] for s in segments), reference.get("critical_spans", []))
    report.update({
        "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
        "observed_output_sha256": hashlib.sha256(observed_bytes).hexdigest(),
        "reference_provenance_as_supplied": reference["provenance"],
        "inference_performed_by_this_command": False,
        "audio_model_revision_and_alignment": "Must be verified against the source run receipt; this scorer does not infer them from current configuration",
    })
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--observed", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_report(args.reference, args.observed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # A score is an immutable evaluation artifact; never overwrite gold, raw output,
    # or an earlier report by accidentally reusing a path.
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print(json.dumps({"wer": report["wer"], "critical_categories": report["critical_categories"], "report": str(args.output)}))


if __name__ == "__main__":
    main()
