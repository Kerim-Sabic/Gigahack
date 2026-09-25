"""Rehearse the real complete app inside a loopback-only Linux namespace.

Prepare dependencies/assets online first. No fixtures replace production inference.
This does not isolate or qualify the surrounding Windows host or target laptop.
"""

import argparse
import errno
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time


def network_proof():
    links = json.loads(subprocess.check_output(["ip", "-j", "link", "show"], text=True))
    probes = {}
    for label, family, address in [
        ("ipv4", socket.AF_INET, ("1.1.1.1", 443)),
        ("ipv6", socket.AF_INET6, ("2606:4700:4700::1111", 443)),
    ]:
        with socket.socket(family, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            try:
                connection.connect(address)
                probes[label] = {"blocked": False}
            except OSError as exc:
                probes[label] = {
                    "blocked": exc.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH),
                    "errno": exc.errno,
                }
    return {
        "namespace": os.readlink("/proc/self/ns/net"),
        "interfaces": [link["ifname"] for link in links],
        "external_probes": probes,
        "enforced": {link["ifname"] for link in links} == {"lo"}
        and all(p["blocked"] for p in probes.values()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="Prepared synthetic audio file")
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "linux":
        raise SystemExit("Run under prepared Linux/WSL. Windows host networking is not changed.")
    source = Path(args.path).resolve(strict=True)
    own = os.readlink("/proc/self/ns/net")
    if not args.inside:
        data = tempfile.mkdtemp(prefix="secure-mom-isolated-app-", dir="/var/tmp")
        env = {**os.environ, "MOM_DATA": data, "_MOM_APP_PARENT_NETNS": own}
        print("Fresh synthetic qualification data: " + data, flush=True)
        result = subprocess.run(
            [
                "unshare",
                "-Urn",
                sys.executable,
                "-m",
                "scripts.qualify_isolated_app",
                "--inside",
                "--path",
                str(source),
            ],
            env=env,
        )
        raise SystemExit(result.returncode)
    if own == os.environ.get("_MOM_APP_PARENT_NETNS") or not os.environ.get("_MOM_APP_PARENT_NETNS"):
        raise SystemExit("Refusing changes in the parent/host network namespace")
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True, timeout=10)
    before = network_proof()
    if not before["enforced"]:
        raise SystemExit("Loopback-only isolation proof failed before startup")
    # Fresh test services never use inherited production mail credentials or proxies.
    for key in list(os.environ):
        if key.upper().endswith("_PROXY") or key in (
            "MOM_SMTP_USER",
            "MOM_SMTP_PASSWORD",
            "MOM_SMTP_CA_FILE",
            "MOM_ISOLATE_WORKER",
        ):
            os.environ.pop(key)
    os.environ.update(
        {
            "MOM_SMTP_HOST": "127.0.0.1",
            "MOM_SMTP_PORT": "1025",
            "MOM_SMTP_TLS": "none",
            "MOM_QUALIFY_USER": "synthetic-isolated-reviewer",
            "MOM_QUALIFY_PASSWORD": secrets.token_urlsafe(24),
            "MOM_SYNTHETIC_AUDIO": str(source),
        }
    )
    from services.api import config
    from scripts.mom import start, stop
    from scripts.browser_e2e import main as browser
    from services.worker.process_identity import matches
    import psutil

    started = time.monotonic()
    report = {
        "kind": "real-linux-isolated-complete-app",
        "scope": "Browser, API, FFmpeg, production inference, PDF and Mailpit in one Linux namespace",
        "before": before,
        "result": "failed",
        "windows_host": "outside this scope",
        "target_laptop": "NOT RUN",
        "semantic_accuracy": "not established by a synthetic workflow",
    }
    services = []
    try:
        start()
        services = json.loads((config.DATA / "processes.json").read_text())
        report["service_namespaces"] = {r["name"]: os.readlink(f"/proc/{r['pid']}/ns/net") for r in services}
        if not all(ns == own for ns in report["service_namespaces"].values()):
            raise RuntimeError("Service escaped the qualification namespace")
        browser()
        report["workflow"] = json.loads((config.DATA / "proofs/browser-e2e.json").read_text())
        report["after"] = network_proof()
        report["stages"] = [
            json.loads(p.read_text()) for p in (config.DATA / "jobs").glob("*/*-receipt.json")
        ]
        if not report["after"]["enforced"]:
            raise RuntimeError("Post-workflow isolation proof failed")
        report["result"] = "passed"
    except BaseException as exc:
        report["error_type"] = type(exc).__name__
        raise
    finally:
        try:
            stop()
            remaining = []
            for record in services:
                try:
                    if matches(record) and psutil.Process(record["pid"]).status() != psutil.STATUS_ZOMBIE:
                        remaining.append(record["name"])
                except psutil.NoSuchProcess:
                    pass
            report["cleanup"] = {"remaining_owned_services": remaining}
            if remaining:
                raise RuntimeError("Qualification left managed services running")
        except BaseException:
            report["result"] = "failed"
            report["cleanup_failed"] = True
            raise
        finally:
            report["elapsed_seconds"] = time.monotonic() - started
            (config.DATA / "proofs").mkdir(parents=True, exist_ok=True)
            (config.DATA / "proofs/isolated-app.json").write_text(json.dumps(report, indent=2))
            print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
