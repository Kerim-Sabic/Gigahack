"""Explicit CI-only inference fixture. Production runtime never imports this module.

The browser, API, queue, persistence, evidence checks, PDF and Mailpit are real.
The silence WAV and fixed transcript test plumbing, never model accuracy.
"""

import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import uuid
import wave

TEXT = "Elena sends the report on 30 September. Confirmed."


def fixture_stage(job, stage, spec):
    if stage == "whisper":
        return {"segments": [{"start": 0, "end": 32000, "text": TEXT, "raw": {"fixture": True}, "words": []}]}
    if stage != "extract":
        raise RuntimeError("CI fixture does not implement optional inference")
    source = spec["segments"][0]
    return {
        "events": [
            {
                "subject": "report",
                "category": "action",
                "kind": "confirm",
                "text": "Send report",
                "owner": "Elena",
                "raw_due": "30 September",
                "due": "2026-09-30",
                "condition": None,
                "value": None,
                "changed_fields": [],
                "uncertainties": ["Explicit test-only inference fixture"],
                "evidence": [
                    {
                        "segment_id": source["id"],
                        "revision": source["revision"],
                        "field": field,
                        "quote": quote,
                    }
                    for field, quote in [
                        ("text", TEXT),
                        ("owner", "Elena"),
                        ("due", "30 September"),
                        ("kind", "Confirmed."),
                    ]
                ],
            }
        ]
    }


def worker():
    from services.worker import supervisor

    # This injection exists exclusively in the test process. No environment variable
    # or meeting title can activate a fixture in the production worker.
    supervisor.run_stage = fixture_stage
    supervisor.main()


def main():
    root = Path(__file__).resolve().parents[1]
    for port in (8765, 8025, 1025):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(
                    "Stop managed development services before fixture E2E; occupied ports are never killed."
                )
    data = root / ".runtime" / ("fixture-" + uuid.uuid4().hex)
    data.mkdir(parents=True)
    os.environ.update(
        {
            "MOM_DATA": str(data),
            "MOM_QUALIFY_USER": "fixture-secretary",
            "MOM_QUALIFY_PASSWORD": secrets.token_urlsafe(24),
        }
    )
    fixture = data / "synthetic-silence.wav"
    with wave.open(str(fixture), "wb") as f:
        f.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        f.writeframes(b"\x00\x00" * 32000)
    os.environ["MOM_SYNTHETIC_AUDIO"] = str(fixture)
    from services.api.db import migrate
    from services.worker.supervisor import kill_tree
    from scripts.browser_e2e import main as browser
    import httpx

    migrate()
    binary = next((root / ".runtime/tools/mailpit").rglob("mailpit.exe" if os.name == "nt" else "mailpit"))
    commands = [
        [
            str(binary),
            "--listen",
            "127.0.0.1:8025",
            "--smtp",
            "127.0.0.1:1025",
            "--database",
            str(data / "mail.sqlite"),
        ],
        [
            sys.executable,
            "-m",
            "uvicorn",
            "services.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
            "--no-access-log",
        ],
        [sys.executable, "-m", "tests.browser_fixture", "--worker"],
        [sys.executable, "-m", "services.worker.supervisor", "--mail-only"],
    ]
    processes = []
    try:
        for i, command in enumerate(commands):
            with (data / f"process-{i}.log").open("wb") as log:
                processes.append(
                    subprocess.Popen(
                        command,
                        cwd=root,
                        stdout=log,
                        stderr=log,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                )
        for _ in range(30):
            if any(p.poll() is not None for p in processes):
                raise RuntimeError("Fixture service exited; inspect test-local logs")
            try:
                if httpx.get("http://127.0.0.1:8765/api/v1/setup", trust_env=False).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        browser(fixture_inference=True)
        from scripts.ui_language_e2e import main as check_languages

        check_languages()
    finally:
        for process in reversed(processes):
            kill_tree(process.pid)


if __name__ == "__main__":
    worker() if "--worker" in sys.argv else main()
