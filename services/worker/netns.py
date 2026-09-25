"""Entered ONLY after unshare creates a dedicated unprivileged network namespace."""

import json
import os
import socket
import subprocess
import sys
import time

from services.api.config import DATA


def main():
    if sys.platform != "linux":
        raise SystemExit("Network namespace isolation requires Linux/WSL.")
    # Refuse accidentally executing this module directly in the host namespace.
    own = os.readlink("/proc/self/ns/net")
    parent = os.environ.get("_MOM_PARENT_NETNS")
    if not parent:
        result = subprocess.run(
            ["unshare", "-Urn", sys.executable, "-m", "services.worker.netns"],
            env={**os.environ, "_MOM_PARENT_NETNS": own},
        )
        raise SystemExit(result.returncode)
    if own == parent:
        raise SystemExit("Refusing host namespace changes; run through unshare -Urn.")
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True, timeout=10)
    checks = {}
    for family, address in [
        (socket.AF_INET, ("1.1.1.1", 443)),
        (socket.AF_INET6, ("2606:4700:4700::1111", 443)),
    ]:
        with socket.socket(family, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            try:
                s.connect(address)
                checks[str(family)] = "UNEXPECTED CONNECTION"
            except OSError as exc:
                checks[str(family)] = {"blocked": True, "errno": exc.errno}
    routes = subprocess.run(
        ["ip", "route", "show", "table", "all"], capture_output=True, text=True, check=True
    ).stdout
    report = {
        "scope": "dedicated inference namespace only; not Windows host or API",
        "checked_at": time.time(),
        "namespace": own,
        "external_probe": checks,
        "routes": routes,
        "enforced": all(isinstance(v, dict) and v["blocked"] for v in checks.values()),
    }
    (DATA / "proofs").mkdir(parents=True, exist_ok=True)
    (DATA / "proofs/worker-network.json").write_text(json.dumps(report, indent=2))
    if not report["enforced"]:
        raise SystemExit("Namespace external probe unexpectedly succeeded.")
    os.execv(sys.executable, [sys.executable, "-m", "services.worker.supervisor"])


if __name__ == "__main__":
    main()
