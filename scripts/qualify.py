import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from services.api.config import DATA, ROOT


def qualify(audio):
    from scripts.mom import doctor, verify_assets

    if not audio or not Path(audio).is_file():
        raise SystemExit("Supply --path to a synthetic audio fixture. No prerecorded answers are used.")
    DATA.mkdir(parents=True, exist_ok=True)
    report = {
        "environment": doctor(),
        "checks": {},
        "started": time.time(),
        "fixture_sha256": hashlib.sha256(Path(audio).read_bytes()).hexdigest(),
        "human_accuracy": "not measured",
        "thermals": "not measured",
        "host_egress": "not measured",
    }
    try:
        verify_assets()
        report["checks"]["assets"] = True
        if not os.environ.get("MOM_QUALIFY_USER") or not os.environ.get("MOM_QUALIFY_PASSWORD"):
            raise RuntimeError(
                "Set MOM_QUALIFY_USER and MOM_QUALIFY_PASSWORD for the local synthetic test account."
            )
        env = {**os.environ, "MOM_SYNTHETIC_AUDIO": str(Path(audio).resolve())}
        result = subprocess.run([sys.executable, "-m", "scripts.browser_e2e"], cwd=ROOT, env=env, timeout=600)
        report["checks"]["real_browser_workflow"] = result.returncode == 0
        receipts = []
        for path in (DATA / "jobs").glob("*/*-receipt.json"):
            if path.stat().st_mtime >= report["started"]:
                receipts.append(json.loads(path.read_text()))
        gpu = [r["peak_total_gpu0_mib"] for r in receipts if r.get("peak_total_gpu0_mib") is not None]
        ram = [r["peak_host_ram_bytes"] for r in receipts if r.get("peak_host_ram_bytes") is not None]
        report["stage_measurements"] = receipts
        report["checks"]["target_memory_budgets"] = (
            bool(gpu and ram) and max(gpu) < 7168 and max(ram) < 20 * 1024**3
        )
        report["unverified"] = [
            "thermal sustained load",
            "Windows/WSL egress boundaries",
            "human RO/RU/EN accuracy",
        ]
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        report["elapsed_seconds"] = time.time() - report["started"]
        path = DATA / "proofs/qualification.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    if not report["checks"] or not all(report["checks"].values()):
        raise SystemExit(1)
