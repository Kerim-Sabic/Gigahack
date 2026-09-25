import hashlib
import json
import os
import smtplib
import ssl
import subprocess
import sys
import tempfile
import time
from email.message import EmailMessage
from pathlib import Path

import psutil
from filelock import FileLock, Timeout

from services.api import config
from services.api.db import canonical, migrate, transaction, uid
from services.api.domain import Candidate, event_key, validate_evidence
from services.api.dates import resolve
from services.api.provenance import runtime_identity


def kill_tree(pid):
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
    except psutil.NoSuchProcess:
        return
    for process in [*reversed(children), parent]:
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs([parent, *children], timeout=5)
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(alive, timeout=5)


def stage_environment():
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "CUDA_VISIBLE_DEVICES": "0"}
    if sys.platform == "linux":
        libraries = sorted(Path(sys.prefix).glob("lib/python*/site-packages/nvidia/*/lib"))
        libraries += sorted({p.parent for p in (config.ROOT / ".runtime/tools/llama").rglob("*.so*")})
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join([*(str(p) for p in libraries), *([existing] if existing else [])])
    return env


def run_stage(job, stage, spec):
    folder = config.DATA / "jobs" / job["id"]
    folder.mkdir(parents=True, exist_ok=True)
    spec["run_dir"] = str(folder)
    source = folder / f"{stage}-input.json"
    target = folder / f"{stage}-output.json"
    source.write_text(canonical(spec), encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    receipt = folder / f"{stage}-receipt.json"
    if target.exists() and receipt.exists() and json.loads(receipt.read_text())["input_hash"] == digest:
        return json.loads(target.read_text(encoding="utf-8"))
    with transaction() as c:
        c.execute("UPDATE jobs SET stage=?,lease=? WHERE id=?", (stage, time.time() + 30, job["id"]))
        c.execute(
            "UPDATE meetings SET status=? WHERE id=?",
            ("transcribing" if stage == "whisper" else "reconciling", job["meeting_id"]),
        )
    # Discard the previous attempt's display before this attempt starts.
    try:
        (folder / "progress.json").unlink(missing_ok=True)
    except OSError:
        pass  # Display artifacts do not authorize or block inference.
    log = open(folder / f"{stage}.log", "wb")
    env = stage_environment()
    from services.worker.resources import ResourceSampler

    sampler = ResourceSampler()
    proc = subprocess.Popen(
        [sys.executable, "-m", "services.worker.stage", stage, str(source), str(target)],
        stdout=log,
        stderr=log,
        cwd=config.ROOT,
        env=env,
    )
    started = time.time()
    last_resource_sample = 0
    try:
        while proc.poll() is None:
            with transaction() as c:
                row = c.execute("SELECT cancel FROM jobs WHERE id=?", (job["id"],)).fetchone()
                c.execute("UPDATE jobs SET lease=? WHERE id=?", (time.time() + 30, job["id"]))
            if row["cancel"]:
                raise RuntimeError("cancelled")
            if time.time() - started > 7200:
                raise RuntimeError("stage_timeout")
            if time.monotonic() - last_resource_sample >= 1:
                last_resource_sample = time.monotonic()
                sampler.sample(proc.pid)
            time.sleep(0.5)
        if proc.returncode != 0:
            log.flush()
            tail = (folder / f"{stage}.log").read_bytes()[-8192:].lower()
            if b"out of memory" in tail or b"cuda_error_out_of_memory" in tail:
                raise RuntimeError(stage + "_oom")
            raise RuntimeError(stage + "_failed_see_local_log")
        output = json.loads(target.read_text(encoding="utf-8"))
        resources = sampler.report()
        gpu0 = next((d for d in resources["gpu_devices"] if d["index"] == "0"), {})
        receipt.write_text(
            canonical(
                {
                    "input_hash": digest,
                    "output_hash": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "elapsed_seconds": time.time() - started,
                    "peak_process_ram_bytes": resources["peak_process_tree_rss_bytes"],
                    "peak_total_gpu0_mib": gpu0.get("peak_total_mib"),
                    "peak_host_ram_bytes": resources["peak_host_used_bytes"],
                    "peak_gpu_temperature_c": gpu0.get("peak_temperature_c"),
                    "memory_scope": "GPU 0 total includes desktop; host RAM includes unrelated processes",
                    "resources": resources,
                    "contract_version": 2,
                }
            ),
            encoding="utf-8",
        )
        return output
    finally:
        if proc.poll() is None:
            kill_tree(proc.pid)
        proc.wait()
        log.close()
        try:
            (folder / f"{stage}-resources.json").write_text(canonical(sampler.report()), encoding="utf-8")
        except OSError:
            pass  # A failed diagnostics write must not mask the stage failure or cleanup.


def retry_stage(job, stage, spec):
    try:
        return run_stage(job, stage, spec)
    except RuntimeError as exc:
        if str(exc) != stage + "_oom":
            raise
        smaller = {**spec, "config": {**spec["config"], "oom_retry": True}}
        with transaction() as c:
            c.execute(
                "UPDATE jobs SET error=? WHERE id=?",
                ("OOM: retrying once with smaller windows/batches", job["id"]),
            )
        return run_stage(job, stage, smaller)


def process(job):
    queued_config = json.loads(job["config"])
    if queued_config.get("implementation") and queued_config["implementation"] != runtime_identity():
        raise RuntimeError("implementation_changed_queue_new_job")
    with transaction() as c:
        asset = dict(c.execute("SELECT * FROM assets WHERE id=?", (job["asset_id"],)).fetchone())
        meeting = dict(c.execute("SELECT * FROM meetings WHERE id=?", (job["meeting_id"],)).fetchone())
    manifest = config.ROOT / "manifests/models.lock.json"
    prompt_file = config.ROOT / "services/worker/stage.py"
    spec = {
        "audio": asset["path"],
        "config": json.loads(job["config"]),
        "meeting": meeting,
        "model_manifest_hash": hashlib.sha256(manifest.read_bytes()).hexdigest()
        if manifest.exists()
        else None,
        "prompt_code_hash": hashlib.sha256(prompt_file.read_bytes()).hexdigest(),
        "input_audio_hash": asset["hash"],
    }
    asr = retry_stage(job, "whisper", spec)
    with transaction() as c:
        existing = c.execute(
            "SELECT * FROM segments WHERE asset_id=? ORDER BY start", (asset["id"],)
        ).fetchall()
        if not existing:
            for s in asr["segments"]:
                c.execute(
                    "INSERT INTO segments(id,meeting_id,asset_id,revision,start,end,text,raw,words) VALUES(?,?,?,1,?,?,?,?,?)",
                    (
                        uid(),
                        meeting["id"],
                        asset["id"],
                        s["start"],
                        s["end"],
                        s["text"],
                        canonical(s["raw"]),
                        canonical(s["words"]),
                    ),
                )
        segments = [
            dict(r)
            for r in c.execute("SELECT * FROM segments WHERE asset_id=? ORDER BY start", (asset["id"],))
        ]
    from .optional import optional_stages

    optional_stages(job, spec, asset, segments, run_stage)
    with transaction() as c:
        segments = [
            dict(r)
            for r in c.execute("SELECT * FROM segments WHERE asset_id=? ORDER BY start", (asset["id"],))
        ]
    spec["segments"] = [{k: s[k] for k in ("id", "revision", "start", "end", "text")} for s in segments]
    extracted = retry_stage(job, "extract", spec) if segments else {"events": []}
    source = {s["id"]: s for s in segments}
    validated = []
    for e in extracted["events"]:
        event = Candidate.model_validate(e)
        for ref in event.evidence:
            segment = source[ref.segment_id]
            if json.loads(segment["raw"]).get("boundary_review"):
                event.uncertainties.append("Source crosses an audio processing boundary; verify wording against the audio")
            if json.loads(segment["alternatives"]):
                for alternative in json.loads(segment["alternatives"]):
                    if alternative["text"].strip() != segment["text"].strip():
                        event.uncertainties.append("Two recognizers disagree; inspect complete hypotheses")
                        if event.value is not None:
                            event.value = None
                            event.quantity = None
                            event.uncertainties.append(
                                "Critical numeric value withheld pending review of ASR disagreement"
                            )
            if segment.get("speaker") == "Unknown / overlapping speakers":
                event.uncertainties.append("Speaker overlap: identity must not be inferred")
        if event.raw_due:
            event.due = resolve(event.raw_due, meeting["date"])
            if not event.due:
                event.uncertainties.append(
                    "Date expression unresolved; reviewer must inspect original expression"
                )
        validated.append((event, validate_evidence(event, source)))
    with transaction() as c:
        for s in segments:
            current = c.execute("SELECT revision FROM segments WHERE id=?", (s["id"],)).fetchone()
            if not current or current["revision"] != s["revision"]:
                raise RuntimeError("transcript_changed_during_extraction")
        if queued_config.get("implementation") and queued_config["implementation"] != runtime_identity():
            raise RuntimeError("implementation_changed_queue_new_job")
        c.execute(
            "UPDATE candidates SET review='excluded' WHERE review='needs_review' AND id IN (SELECT e.candidate_id FROM evidence e JOIN segments s ON s.id=e.segment_id WHERE s.asset_id=?)",
            (asset["id"],),
        )
        for event, evidence in validated:
            body = event.model_dump()
            ident = event_key(body)
            # Scope semantic key to meeting; same utterance in another meeting is distinct.
            ident = hashlib.sha256((meeting["id"] + ident).encode()).hexdigest()
            if c.execute("SELECT 1 FROM candidates WHERE id=?", (ident,)).fetchone():
                continue
            chronology = [e for e in evidence if e["field"] == "kind"] or [
                e for e in evidence if e["field"] == "text"
            ]
            position = max(source[e["segment_id"]]["start"] * 1000000 + e["start"] for e in chronology)
            c.execute(
                "INSERT INTO candidates(id,meeting_id,subject,body,source_order,created) VALUES(?,?,?,?,?,?)",
                (ident, meeting["id"], event.subject, canonical(body), position, time.time()),
            )
            for e in evidence:
                c.execute(
                    "INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        uid(),
                        meeting["id"],
                        ident,
                        e["segment_id"],
                        e["revision"],
                        e["field"],
                        e["quote"],
                        e["start"],
                        e["end"],
                    ),
                )
        c.execute("UPDATE jobs SET state='complete',stage='awaiting_review',lease=0 WHERE id=?", (job["id"],))
        c.execute(
            "UPDATE meetings SET status='awaiting_review',revision=revision+1 WHERE id=?", (meeting["id"],)
        )


def deliver_one():
    with transaction() as c:
        c.execute(
            "UPDATE outbox SET state='uncertain',error='worker_interrupted_during_send' WHERE state='sending'"
        )
        row = c.execute(
            "SELECT o.*,s.html,s.body FROM outbox o JOIN snapshots s ON s.id=o.snapshot_id WHERE o.state='queued' ORDER BY o.created LIMIT 1"
        ).fetchone()
        if not row:
            return False
        row = dict(row)
        c.execute("UPDATE outbox SET state='sending',attempt=attempt+1 WHERE id=?", (row["id"],))
    state, error = "smtp_accepted", None
    entered_data = False
    try:
        msg = EmailMessage()
        msg["From"] = os.environ.get("MOM_SMTP_FROM", "minutes@secure-mom.test")
        msg["To"] = ", ".join(json.loads(row["addresses"]))
        msg["Subject"] = "Approved minutes: " + json.loads(row["body"])["meeting"]["title"]
        msg["Message-ID"] = row["message_id"]
        msg.set_content("Approved meeting minutes are included as HTML. No audio attached.")
        msg.add_alternative(row["html"], subtype="html")
        host = os.environ.get("MOM_SMTP_HOST", "127.0.0.1")
        local = host.lower() in ("127.0.0.1", "::1", "localhost")
        mode = os.environ.get("MOM_SMTP_TLS", "none" if local else "starttls")
        if mode not in ("none", "starttls", "ssl") or (mode == "none" and not local):
            raise ValueError("TLS is required for non-loopback SMTP")
        username, password = os.environ.get("MOM_SMTP_USER"), os.environ.get("MOM_SMTP_PASSWORD")
        if bool(username) != bool(password) or (username and mode == "none"):
            raise ValueError("SMTP authentication requires credentials and TLS")
        port = int(os.environ.get("MOM_SMTP_PORT", "1025" if local else "465" if mode == "ssl" else "587"))
        context = (
            ssl.create_default_context(cafile=os.environ.get("MOM_SMTP_CA_FILE")) if mode != "none" else None
        )
        transport = smtplib.SMTP_SSL if mode == "ssl" else smtplib.SMTP
        with transport(host, port, timeout=15, **({"context": context} if mode == "ssl" else {})) as smtp:
            if mode == "starttls":
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
            if username:
                smtp.login(username, password)
            entered_data = True
            refused = smtp.send_message(msg)
            if refused:
                state, error = "uncertain", "some_recipients_refused"
    except Exception:
        state, error = ("uncertain" if entered_data else "failed"), "smtp_transport_error"
    with transaction() as c:
        c.execute("UPDATE outbox SET state=?,error=? WHERE id=?", (state, error, row["id"]))
    return True


def tick():
    with transaction() as c:
        c.execute(
            "UPDATE jobs SET state='queued',error='lease_recovered' WHERE state='running' AND lease<?",
            (time.time(),),
        )
        c.execute("UPDATE jobs SET state='cancelled' WHERE state='queued' AND cancel=1")
        row = c.execute(
            "SELECT * FROM jobs WHERE state='queued' AND cancel=0 ORDER BY created LIMIT 1"
        ).fetchone()
        if not row:
            return False
        job = dict(row)
        c.execute(
            "UPDATE jobs SET state='running',lease=?,attempt=attempt+1 WHERE id=?",
            (time.time() + 30, job["id"]),
        )
    try:
        process(job)
    except Exception as exc:
        code = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        with transaction() as c:
            state = "cancelled" if code == "cancelled" else "failed"
            c.execute("UPDATE jobs SET state=?,error=?,lease=0 WHERE id=?", (state, code[:160], job["id"]))
            c.execute("UPDATE meetings SET status='failed' WHERE id=?", (job["meeting_id"],))
    return True


def main():
    migrate()
    if "--mail-only" in sys.argv:
        with FileLock(str(config.DATA / "mail-worker.lock"), timeout=0):
            while True:
                deliver_one()
                time.sleep(1)
        return
    # Shared across app data directories so a second installation cannot double-admit models.
    lock = FileLock(str(Path(tempfile.gettempdir()) / "secure-mom-gpu.lock"), timeout=0)
    try:
        with lock:
            while True:
                tick()
                time.sleep(1)
    except Timeout:
        raise SystemExit("Another Secure MOM supervisor owns GPU admission.")


if __name__ == "__main__":
    main()
