"""Real Linux inference in an isolated namespace, using a synthetic 16 kHz mono PCM WAV."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import wave


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        raise SystemExit("Run this scoped verification under Linux/WSL; the Windows host is not modified.")
    source = Path(args.path).resolve()
    with wave.open(str(source)) as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (16000, 1, 2):
            raise SystemExit("Provide a synthetic 16 kHz mono 16-bit PCM WAV, prepared while online.")
        samples = audio.getnframes()
    from services.api import config
    from services.api.db import migrate, uid, transaction, canonical
    from services.worker.supervisor import kill_tree

    data = config.DATA / ("isolated-qualification-" + uid())
    config.DATA = data
    migrate()
    audio_path = data / "audio/source.wav"
    shutil.copy2(source, audio_path)
    meeting, asset, job = uid(), uid(), uid()
    with transaction() as c:
        c.execute(
            "INSERT INTO meetings(id,title,date,timezone,language,classification,created) VALUES(?,?,'2026-09-25','Europe/Chisinau','en','synthetic',?)",
            (meeting, "Synthetic scoped Linux inference qualification", time.time()),
        )
        c.execute(
            "INSERT INTO assets VALUES(?,?,?,?,16000,?,1,?)",
            (
                asset,
                meeting,
                str(audio_path),
                hashlib.sha256(audio_path.read_bytes()).hexdigest(),
                samples,
                str(audio_path),
            ),
        )
        c.execute(
            "INSERT INTO jobs(id,meeting_id,asset_id,state,stage,config,created) VALUES(?,?,?,'queued','queued',?,?)",
            (
                job,
                meeting,
                asset,
                canonical({"device": "cuda", "parakeet": False, "diarization": False}),
                time.time(),
            ),
        )
    log = (data / "worker.log").open("wb")
    process = subprocess.Popen(
        [sys.executable, "-m", "services.worker.netns"],
        cwd=config.ROOT,
        env={**os.environ, "MOM_DATA": str(data)},
        stdout=log,
        stderr=log,
        start_new_session=True,
    )
    started = time.monotonic()
    try:
        while time.monotonic() - started < 600:
            with transaction() as c:
                result = dict(c.execute("SELECT state,stage,error FROM jobs WHERE id=?", (job,)).fetchone())
            if result["state"] in ("complete", "failed", "cancelled"):
                break
            if process.poll() is not None:
                raise RuntimeError("Namespace worker exited; inspect qualification-local logs")
            time.sleep(1)
        else:
            raise RuntimeError("Isolated inference timeout")
        boundary = json.loads((data / "proofs/worker-network.json").read_text())
        report = {
            "kind": "real-linux-isolated-worker",
            "job": result,
            "boundary": boundary,
            "elapsed_seconds": time.monotonic() - started,
            "windows_host": "not measured",
            "api_pdf_smtp": "outside this scoped test",
            "target_laptop": "not run",
            "stages": [json.loads(p.read_text()) for p in (data / "jobs" / job).glob("*-receipt.json")],
        }
        (data / "proofs/result.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        if result["state"] != "complete" or not boundary["enforced"]:
            raise SystemExit(1)
    finally:
        kill_tree(process.pid)
        log.close()


if __name__ == "__main__":
    main()
