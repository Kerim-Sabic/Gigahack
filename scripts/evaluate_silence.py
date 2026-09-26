"""T26 generated silence or original instrumental audio through the production worker.

The generated tune does not qualify arbitrary music, overlap or multilingual speech.
"""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import wave
import math
import struct

from filelock import FileLock

from services.api import config
from services.api.db import canonical, migrate, transaction, uid
from services.api.provenance import runtime_identity
from services.worker.supervisor import process


def main(condition="silence"):
    if condition not in {"silence", "music"}:
        raise ValueError("unknown_nonspeech_condition")
    data = config.DATA / "evaluations" / (condition + "-" + str(time.time_ns()))
    config.DATA = data
    os.environ["MOM_DATA"] = str(data.resolve())
    migrate()
    audio = data / ("audio/synthetic-" + condition + ".wav")
    with wave.open(str(audio), "wb") as output:
        output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        if condition == "silence":
            output.writeframes(b"\0\0" * (20 * 16000))
        else:
            # Original procedural instrumental fixture; no borrowed recording,
            # voice, pretrained synthesizer or third-party musical composition.
            notes = (261.63, 329.63, 392.00, 293.66, 349.23, 440.00, 329.63, 261.63)
            frames = bytearray()
            for sample in range(20 * 16000):
                t = sample / 16000
                phase = t % 0.5
                envelope = min(1, phase / 0.02) * max(0, 1 - phase / 0.48)
                frequency = notes[int(t * 2) % len(notes)]
                value = envelope * (0.3 * math.sin(2 * math.pi * frequency * t) + 0.08 * math.sin(4 * math.pi * frequency * t))
                frames.extend(struct.pack("<h", round(32767 * value)))
            output.writeframes(frames)
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
            "INSERT INTO meetings(id,title,date,timezone,language,classification,revision,status,created) VALUES(?,?,'2026-09-25','Europe/Chisinau','en','Administrative',1,'queued',?)",
            (meeting, "Synthetic " + condition + " evaluation", time.time()),
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
        "scope": "20 seconds generated " + condition + "; only this nonspeech fixture, not arbitrary music/speech",
        "condition": condition,
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "provenance": "locally generated synthetic waveform; no recorded people or external assets",
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
            raise RuntimeError("Unexpected speech/content from " + condition)
        report["status"] = "PASS"
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        (data / "proofs/result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=("silence", "music"), default="silence")
    main(parser.parse_args().condition)
