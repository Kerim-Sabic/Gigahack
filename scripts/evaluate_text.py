"""Run actual local extraction on all 30 adversarial texts; preserve observed failures."""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from filelock import FileLock
import tempfile
from services.api.config import DATA, ROOT
from services.api.domain import Candidate, validate_evidence, reduce_events
from services.worker.supervisor import stage_environment


def evaluate():
    cases = json.loads((ROOT / "tests/fixtures/adversarial.json").read_text(encoding="utf-8"))
    folder = DATA / "evaluations"
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    lock = FileLock(str(Path(tempfile.gettempdir()) / "secure-mom-gpu.lock"), timeout=1)
    with lock:
        for case in cases:
            ident = case["id"]
            if case["acoustic_required"] or ident == "T22":
                results.append(
                    {
                        "id": ident,
                        "expected": case["expected"],
                        "status": "NOT RUN",
                        "reason": "Requires audio or stateful integration; condition prose is not observed speech.",
                    }
                )
                (folder / "text-results.json").write_text(
                    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(ident, "NOT RUN: audio/stateful prerequisite", flush=True)
                continue
            parts = re.findall("“(.*?)”", case["input"]) or [case["input"]]
            segments = [
                {"id": str(i), "revision": 1, "start": i * 16000, "end": (i + 1) * 16000, "text": text}
                for i, text in enumerate(parts)
            ]
            spec = {
                "config": {"device": "cuda"},
                "meeting": {"date": "2026-09-25", "timezone": "Europe/Chisinau"},
                "segments": segments,
                "run_dir": str(folder),
            }
            source, target = folder / (ident + "-input.json"), folder / (ident + "-output.json")
            source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            started = time.time()
            run = subprocess.run(
                [sys.executable, "-m", "services.worker.stage", "extract", str(source), str(target)],
                capture_output=True,
                timeout=240,
                cwd=ROOT,
                env=stage_environment(),
            )
            row = {
                "id": ident,
                "expected": case["expected"],
                "elapsed_seconds": time.time() - started,
                "acoustic_required": case["acoustic_required"],
            }
            if run.returncode:
                row.update(
                    status="FAIL", error=run.stderr.decode("utf-8", errors="replace").splitlines()[-1:]
                )
            else:
                output = json.loads(target.read_text(encoding="utf-8"))
                row["events"] = output["events"]
                try:
                    for e in output["events"]:
                        validate_evidence(Candidate.model_validate(e), {s["id"]: s for s in segments})
                    rows = [
                        {
                            "id": str(i),
                            "source_order": min(int(e["segment_id"]) for e in ev["evidence"]),
                            "body": ev,
                        }
                        for i, ev in enumerate(output["events"])
                    ]
                    row["projection"] = reduce_events(rows)
                    row["status"] = "REQUIRES SEMANTIC REVIEW"
                except ValueError as exc:
                    row.update(status="FAIL", error=str(exc))
            results.append(row)
            (folder / "text-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(ident, row["status"], flush=True)
    print("Actual outputs saved. Schema/evidence validity does not establish expected semantic outcome.")


if __name__ == "__main__":
    evaluate()
