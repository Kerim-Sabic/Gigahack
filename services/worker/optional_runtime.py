"""Verify the isolated optional environment using metadata only, before heavy imports."""

import hashlib
import importlib.metadata as metadata
import json
import platform
import re
import sys
from pathlib import Path

from services.api import config


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def fingerprint():
    files = (
        "manifests/optional-runtime-candidate.json",
        "manifests/optional-runtime-candidate.lock.txt",
        "manifests/optional-runtime-experiment/patches.json",
    )
    hashes = {name: hashlib.sha256((config.ROOT / name).read_bytes()).hexdigest() for name in files}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def prepared_runtime(prefix):
    """Cheap readiness lookup for the API; actual workers recheck packages and assets."""
    if sys.platform != "linux" or not prefix:
        return None
    root = Path(prefix)
    if not root.is_absolute():
        return None
    try:
        marker = root / "secure-mom-runtime.json"
        if marker.stat().st_size > 65536:
            return None
        report = json.loads(marker.read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            return None
        if (report.get("fingerprint") != fingerprint() or report.get("platform") != "linux"
                or Path(report["prefix"]).resolve() != root.resolve()
                or report.get("models_manifest_sha256") != hashlib.sha256(
                    (config.ROOT / "manifests/optional-models.lock.json").read_bytes()).hexdigest()
                or not (root / "bin/python").is_file()):
            return None
        return report
    except (OSError, ValueError, KeyError, TypeError):
        return None


def stage_python(prefix):
    if prepared_runtime(prefix) is None:
        raise RuntimeError("optional_runtime_not_prepared")
    return str(Path(prefix) / "bin/python")


def verify_runtime():
    if sys.platform != "linux" or platform.machine() != "x86_64" or sys.version_info[:2] != (3, 12):
        raise RuntimeError("optional_runtime_requires_linux_x86_64_python_312")
    manifest = json.loads((config.ROOT / "manifests/optional-runtime-candidate.json").read_text(encoding="utf-8"))
    expected = {normalized(item["name"]): item["version"] for item in manifest["packages"]}
    bootstrap_name, bootstrap_version = manifest["bootstrap"].split("==")
    expected[normalized(bootstrap_name)] = bootstrap_version
    actual = {normalized(dist.metadata["Name"]): dist.version for dist in metadata.distributions()}
    if actual != expected:
        differences = sorted(name for name in actual.keys() | expected.keys() if actual.get(name) != expected.get(name))
        raise RuntimeError("optional_runtime_package_mismatch: " + ", ".join(differences))
    patches = json.loads((config.ROOT / "manifests/optional-runtime-experiment/patches.json").read_text(encoding="utf-8"))
    prefix = Path(sys.prefix).resolve()
    for patch in patches:
        path = Path(metadata.distribution(patch["package"]).locate_file(patch["relative_path"])).resolve()
        if not path.is_relative_to(prefix) or not path.is_file():
            raise RuntimeError("optional_runtime_patch_missing_or_outside_environment")
        if hashlib.sha256(path.read_bytes()).hexdigest() != patch["after"]:
            raise RuntimeError("optional_runtime_patch_mismatch: " + patch["relative_path"])
    return {"fingerprint": fingerprint(), "prefix": str(prefix), "package_count": len(actual),
            "python": platform.python_version(), "platform": sys.platform}


if __name__ == "__main__":
    print(json.dumps(verify_runtime(), indent=2))
