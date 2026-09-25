"""T26 silence branch: real 20-second audio through the production worker.

This does not qualify music, overlapping speakers or human multilingual accuracy.
"""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import wave

from filelock import FileLock

from services.api import config
from services.api.db import canonical, migrate, transaction, uid
from services.api.provenance import runtime_identity
from services.worker.supervisor import process


def main():
    data = config.DATA / "evaluations" / ("silence-" + str(time.time_ns()))
    config.DATA = data
    os.environ["MOM_DATA"] = str(data.resolve())
    migrate()
    audio = data / "audio/synthetic-silence.wav"
    with wave.open(str(audio), "wb") as output:
        output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        output.writeframes(b"\0\0" * (20 * 16000))
    digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    meeting, asset, job_id = uid(), uid(), uid()
    settings = {
        "device": "cuda",
        "parakeet": False,
        "diarization": False,
        "implementation": runtime_identity(),
    }
    with transaction() as db:
        db.execute(
            "INSERT INTO meetings VALUES(?,?,'2026-09-25','Europe/Chisinau','en','Administrative',1,'queued',?)",
            (meeting, "Synthetic silence evaluation", time.time()),
        )
        db.execute(
            "INSERT INTO assets VALUES(?,?,?,?,16000,320000,1,?)",
            (asset, meeting, str(audio.resolve()), digest, canonical({"synthetic": True})),
        )
        db.execute(
            "INSERT INTO jobs(id,meeting_id,asset_id,state,stage,config,created) VALUES(?,?,?,'queued','queued',?,?)",
            (job_id, meeting, asset, canonical(settings), time.time()),
        )
        job = dict(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())
    report = {
        "case": "T26",
        "scope": "20 seconds generated silence; music NOT RUN",
        "audio_sha256": digest,
        "implementation": settings["implementation"],
        "status": "FAIL",
    }
    started = time.monotonic()
    try:
        with FileLock(str(Path(tempfile.gettempdir()) / "secure-mom-gpu.lock"), timeout=1):
            process(job)
        with transaction() as db:
            report["observed_segments"] = db.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
            report["observed_candidates"] = db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
            report["observed_deliveries"] = db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]
        if any(report[key] for key in ("observed_segments", "observed_candidates", "observed_deliveries")):
            raise RuntimeError("Unexpected speech/content from silence")
        report["status"] = "PASS"
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        (data / "proofs/result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
