"""Run with `unshare -Urn python3 scripts/offline_probe.py`; never changes host routes."""

import json
import os
import socket
import subprocess
import sys

own = os.readlink("/proc/self/ns/net")
parent = os.environ.get("_MOM_PARENT_NETNS")
if not parent:
    result = subprocess.run(
        ["unshare", "-Urn", sys.executable, __file__], env={**os.environ, "_MOM_PARENT_NETNS": own}
    )
    raise SystemExit(result.returncode)
if own == parent:
    raise SystemExit("Refusing to alter host namespace")
subprocess.run(["ip", "link", "set", "lo", "up"], check=True)
report = {"scope": "ephemeral Linux namespace only", "ipv4": None, "ipv6": None}
for name, family, target in [
    ("ipv4", socket.AF_INET, ("1.1.1.1", 443)),
    ("ipv6", socket.AF_INET6, ("2606:4700:4700::1111", 443)),
]:
    with socket.socket(family, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        report[name] = s.connect_ex(target)
print(json.dumps(report))
sys.exit(0 if report["ipv4"] and report["ipv6"] else 1)
