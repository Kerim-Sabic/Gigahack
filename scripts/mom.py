"""Cohesive offline runtime and online preparation CLI."""

import argparse
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil

from services.api import config
from services.api.db import migrate
from services.worker.process_identity import identity, matches


def doctor(print_report=True):
    gpu = None
    try:
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    ports = {}
    for port in [8765, 8081, 1025, 8025]:
        with socket.socket() as s:
            ports[port] = "occupied" if s.connect_ex(("127.0.0.1", port)) == 0 else "available"
    report = {
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "gpu": gpu,
        "ram_bytes": psutil.virtual_memory().total,
        "disk_free_bytes": shutil.disk_usage(config.ROOT).free,
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ports": ports,
        "models": {n: (config.MODELS / n).exists() for n in ["whisper", "qwen"]},
        "network_observation": "not measured",
        "target_laptop": "not qualified",
    }
    from scripts.preflight import checks

    report["checks"] = checks(report)
    report["readiness"] = (
        "needs preparation"
        if any(c["status"] == "fail" for c in report["checks"])
        else "ready for local smoke test; qualification remains separate"
    )
    if print_report:
        print(json.dumps(report, indent=2))
    return report


def verify_assets():
    manifest = config.ROOT / "manifests/models.lock.json"
    if not manifest.exists():
        raise SystemExit("Missing model manifest: run prepare-models online.")
    for name, data in json.loads(manifest.read_text()).items():
        for filename, expected in data["files"].items():
            path = config.MODELS / name / filename
            if not path.exists():
                raise SystemExit(f"Missing prepared asset: {name}/{filename}")
            with path.open("rb") as f:
                actual = hashlib.file_digest(f, "sha256").hexdigest()
            if actual != expected:
                raise SystemExit(f"Asset checksum mismatch: {name}/{filename}")
    print("All prepared model checksums verified.")
    from services.worker.assets import verify_tools

    verify_tools()
    print("All prepared native tool checksums verified.")


def start():
    config.init_dirs()
    readiness = doctor(print_report=False)
    failures = [check for check in readiness["checks"] if check["status"] == "fail"]
    if failures:
        raise SystemExit(
            "Preparation incomplete:\n"
            + "\n".join(check["name"] + ": " + check["action"] for check in failures)
        )
    occupied = [str(port) for port, state in readiness["ports"].items() if state == "occupied"]
    if occupied:
        raise SystemExit(
            "Required ports are occupied: "
            + ", ".join(occupied)
            + ". Stop the existing service before starting; unrelated processes are never killed."
        )
    if not (config.ROOT / "apps/web/dist/index.html").exists():
        raise SystemExit("Frontend not prepared. Run npm ci and npm run build in apps/web.")
    verify_assets()
    pidfile = config.DATA / "processes.json"
    if pidfile.exists():
        for p in json.loads(pidfile.read_text()):
            if psutil.pid_exists(p["pid"]):
                raise SystemExit("Recorded service is running. Use stop before starting again.")
    migrate()
    mail = list(
        (config.ROOT / ".runtime/tools/mailpit").rglob("mailpit.exe" if os.name == "nt" else "mailpit")
    )
    if not mail:
        raise SystemExit("Mailpit is missing. Run prepare-tools while online.")
    commands = [
        [
            str(mail[0]),
            "--listen",
            "127.0.0.1:8025",
            "--smtp",
            "127.0.0.1:1025",
            "--database",
            str(config.DATA / "mailpit.sqlite"),
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
        [sys.executable, "-m", "services.worker.supervisor"],
        [sys.executable, "-m", "services.worker.supervisor", "--mail-only"],
    ]
    if os.environ.get("MOM_ISOLATE_WORKER") == "1":
        if sys.platform != "linux" or not shutil.which("unshare"):
            raise SystemExit("MOM_ISOLATE_WORKER requires Linux unshare; no silent fallback.")
        commands[2] = [sys.executable, "-m", "services.worker.netns"]
    records = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        for name, command in zip(["mailpit", "api", "worker", "mail-worker"], commands, strict=True):
            with (config.DATA / f"{name}.log").open("ab") as log:
                p = subprocess.Popen(
                    command,
                    cwd=config.ROOT,
                    stdout=log,
                    stderr=log,
                    creationflags=flags,
                    start_new_session=os.name != "nt",
                )
            records.append(
                {
                    "pid": p.pid,
                    "created": psutil.Process(p.pid).create_time(),
                    "identity": identity(p.pid),
                    "name": name,
                }
            )
        pidfile.write_text(json.dumps(records))
        for _ in range(30):
            for record in records:
                try:
                    process = psutil.Process(record["pid"])
                    alive = process.is_running() and matches(record)
                except psutil.NoSuchProcess:
                    alive = False
                if not alive:
                    raise RuntimeError(f"Service {record['name']} exited during startup; see its local log.")
            try:
                if (
                    httpx.get("http://127.0.0.1:8765/api/v1/system/health", trust_env=False).status_code
                    == 200
                    and httpx.get("http://127.0.0.1:8025/api/v1/messages", trust_env=False).status_code == 200
                ):
                    print("Secure MOM ready: http://127.0.0.1:8765 ; Mailpit: http://127.0.0.1:8025")
                    return
            except httpx.HTTPError:
                pass
            time.sleep(1)
        raise RuntimeError("Startup readiness timed out; see local logs.")
    except BaseException:
        stop()
        raise


def stop():
    from services.worker.supervisor import kill_tree

    path = config.DATA / "processes.json"
    unresolved = []
    if path.exists():
        for record in reversed(json.loads(path.read_text())):
            try:
                p = psutil.Process(record["pid"])
                if matches(record):
                    kill_tree(p.pid)
                    if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                        unresolved.append(record)
                elif "identity" not in record and p.is_running():
                    # Old timestamp-only records cannot distinguish PID reuse from a WSL clock correction.
                    unresolved.append(record)
            except psutil.NoSuchProcess:
                pass
        if unresolved:
            path.write_text(json.dumps(unresolved))
            raise RuntimeError(
                "Some recorded services could not be verified or stopped; process records retained for inspection"
            )
        path.unlink()
    print("Managed services stopped; recordings and database retained.")


def backup(destination):
    if not destination:
        raise SystemExit("Backup requires --path to a new directory.")
    target = Path(destination).resolve()
    if target.exists():
        raise SystemExit("Backup destination must not exist.")
    if target.is_relative_to(config.DATA.resolve()):
        raise SystemExit("Backup destination must be outside the data directory.")
    if not (config.DATA / "app.sqlite").is_file():
        raise SystemExit("No application database exists to back up.")
    # Require stopped services so audio/manifests and SQLite share a consistent boundary.
    if (config.DATA / "processes.json").exists():
        raise SystemExit("Stop managed services before backup.")
    target.mkdir(parents=True)
    with (
        sqlite3.connect(config.DATA / "app.sqlite") as source,
        sqlite3.connect(target / "app.sqlite") as dest,
    ):
        source.backup(dest)
    for name in ["audio", "jobs", "exports", "proofs"]:
        shutil.copytree(config.DATA / name, target / name, dirs_exist_ok=True)
    files = {}
    for file in sorted(target.rglob("*")):
        if file.is_file():
            with file.open("rb") as stream:
                files[file.relative_to(target).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    (target / "backup.json").write_text(
        json.dumps({"version": 2, "original_data_root": str(config.DATA.resolve()), "files": files}),
        encoding="utf-8",
    )
    print("Consistent stopped backup created.")


def restore(source):
    if not source:
        raise SystemExit("Restore requires --path to an existing backup directory.")
    source = Path(source).resolve()
    target = config.DATA.resolve()
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise SystemExit(
            "Restore requires a new empty MOM_DATA directory; existing data is never overwritten."
        )
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise SystemExit("Restore source and destination must be separate directories.")
    metadata = json.loads((source / "backup.json").read_text(encoding="utf-8"))
    if metadata.get("version") not in (1, 2):
        raise SystemExit("Unsupported backup format.")
    if metadata["version"] == 2:
        files = metadata.get("files", {})
        if "app.sqlite" not in files:
            raise SystemExit("Backup manifest is missing its database.")
        for name, expected in files.items():
            file = (source / name).resolve()
            if not file.is_relative_to(source) or not file.is_file():
                raise SystemExit("Backup contains an invalid or missing file.")
            with file.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                    raise SystemExit("Backup checksum mismatch; destination was not changed.")
    else:
        print("Legacy backup: file checksums were not recorded.")
    shutil.copytree(source, target, dirs_exist_ok=True)
    with sqlite3.connect(config.DATA / "app.sqlite") as c:
        for table, column in [("assets", "path"), ("chunks", "path")]:
            c.execute(
                f"UPDATE {table} SET {column}=replace({column},?,?)",
                (metadata["original_data_root"], str(config.DATA.resolve())),
            )
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    print("Backup restored; database integrity check passed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "doctor",
            "prepare-models",
            "prepare-tools",
            "prepare-offline",
            "verify-assets",
            "verify-optional",
            "start",
            "stop",
            "test",
            "backup",
            "restore",
            "qualify-target",
            "qualify-recovery",
        ],
    )
    parser.add_argument("--path")
    parser.add_argument("--wheelhouse", help="Verified prior offline kit wheelhouse; prepare-offline only")
    args = parser.parse_args()
    if args.command == "doctor":
        report = doctor()
        raise SystemExit(1 if any(c["status"] == "fail" for c in report["checks"]) else 0)
    elif args.command == "prepare-models":
        from scripts.prepare_models import prepare

        prepare()
    elif args.command == "prepare-tools":
        from scripts.prepare_tools import prepare

        prepare()
    elif args.command == "prepare-offline":
        from scripts.offline_package import prepare

        prepare(args.path, args.wheelhouse)
    elif args.command == "verify-assets":
        verify_assets()
    elif args.command == "verify-optional":
        if sys.platform != "linux" or not args.path or not Path(args.path).is_absolute():
            raise SystemExit("Use Linux/WSL and --path to the prepared optional environment.")
        python = Path(args.path) / "bin/python"
        if not python.is_file():
            raise SystemExit("Prepared optional Python executable not found.")
        raise SystemExit(subprocess.call([str(python), "-m", "scripts.verify_optional"], cwd=config.ROOT))
    elif args.command == "start":
        start()
    elif args.command == "stop":
        stop()
    elif args.command == "test":
        config.init_dirs()
        raise SystemExit(
            subprocess.call(
                [sys.executable, "-m", "pytest", "-q", "--basetemp", str(config.DATA / "test-temp")]
            )
        )
    elif args.command == "qualify-recovery":
        raise SystemExit(subprocess.call([sys.executable, "-m", "scripts.qualify_crash_recovery"], cwd=config.ROOT))
    elif args.command == "backup":
        backup(args.path)
    elif args.command == "restore":
        restore(args.path)
    else:
        from scripts.qualify import qualify

        qualify(args.path)


if __name__ == "__main__":
    main()
