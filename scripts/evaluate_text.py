"""Run actual local extraction on all 30 adversarial texts; preserve observed failures."""

import json
import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path

from filelock import FileLock
import tempfile
from services.api.config import DATA, ROOT
from services.api.domain import Candidate, validate_evidence, reduce_events
from services.worker.supervisor import stage_environment, kill_tree
from scripts.semantic_checks import check_case


def evaluate(selected=None):
    implementation_hashes = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in (
            "services/worker/stage.py",
            "services/worker/reconcile.py",
            "services/api/domain.py",
            "services/api/dates.py",
            "scripts/semantic_checks.py",
        )
    }
    cases = json.loads((ROOT / "tests/fixtures/adversarial.json").read_text(encoding="utf-8"))
    if selected:
        if set(selected) - {case["id"] for case in cases}:
            raise ValueError("Unknown case identifier")
        cases = [case for case in cases if case["id"] in selected]
    folder = DATA / "evaluations" / str(time.time_ns())
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
            run = subprocess.Popen(
                [sys.executable, "-m", "services.worker.stage", "extract", str(source), str(target)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=ROOT,
                env=stage_environment(),
            )
            try:
                _, stderr = run.communicate(timeout=240)
            except subprocess.TimeoutExpired:
                kill_tree(run.pid)
                _, stderr = run.communicate()
                stderr += b"\nRuntimeError: evaluation_timeout"
            row = {
                "id": ident,
                "expected": case["expected"],
                "elapsed_seconds": time.time() - started,
                "acoustic_required": case["acoustic_required"],
            }
            if run.returncode:
                row.update(status="FAIL", error=stderr.decode("utf-8", errors="replace").splitlines()[-1:])
            else:
                output = json.loads(target.read_text(encoding="utf-8"))
                row["events"] = output["events"]
                try:
                    for e in output["events"]:
                        validate_evidence(Candidate.model_validate(e), {s["id"]: s for s in segments})
                    source_map = {s["id"]: s for s in segments}
                    rows = []
                    for i, ev in enumerate(output["events"]):
                        refs = [e for e in ev["evidence"] if e["field"] == "kind"] or [
                            e for e in ev["evidence"] if e["field"] == "text"
                        ]
                        position = max(
                            source_map[e["segment_id"]]["start"] * 1000000
                            + source_map[e["segment_id"]]["text"].index(e["quote"])
                            for e in refs
                        )
                        rows.append({"id": str(i), "source_order": position, "body": ev})
                    row["projection"] = reduce_events(rows)
                    row["checks"] = check_case(
                        ident, output["events"], row["projection"], "\n".join(s["text"] for s in segments)
                    )
                    row["status"] = (
                        "PASS (AUTOMATED CORPUS CHECKS)" if all(row["checks"].values()) else "FAIL"
                    )
                except ValueError as exc:
                    row.update(status="FAIL", error=str(exc))
            results.append(row)
            (folder / "text-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(ident, row["status"], flush=True)
    summary = {
        "scope": [case["id"] for case in cases],
        "implementation_hashes": implementation_hashes,
        "model_manifest_sha256": hashlib.sha256(
            (ROOT / "manifests/models.lock.json").read_bytes()
        ).hexdigest(),
        "stage_sha256": hashlib.sha256((ROOT / "services/worker/stage.py").read_bytes()).hexdigest(),
        "corpus_sha256": hashlib.sha256((ROOT / "tests/fixtures/adversarial.json").read_bytes()).hexdigest(),
        "passed": sum(r["status"].startswith("PASS") for r in results),
        "failed": sum(r["status"] == "FAIL" for r in results),
        "not_run": sum(r["status"] == "NOT RUN" for r in results),
        "general_accuracy": "NOT MEASURED: fixed development corpus, not held-out hospital audio",
        "report": str(folder / "text-results.json"),
    }
    (folder / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed"] or summary["not_run"] else 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="+")
    raise SystemExit(evaluate(parser.parse_args().cases))
