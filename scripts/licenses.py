"""Collect installed package provenance and preserve supplied license notices."""

import importlib.metadata as md
import argparse
import json
from pathlib import Path

from services.api.config import ROOT


def main(output=None, python_only=False):
    destination = (ROOT / (output or "manifests")).resolve()
    destination.relative_to((ROOT / "manifests").resolve())
    folder = destination / "licenses"
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for dist in md.distributions():
        name = dist.metadata["Name"]
        notices = []
        for f in dist.files or []:
            if "__pycache__" in f.parts or f.suffix == ".pyc":
                continue
            if "dist-info/licenses/" in str(f).replace("\\", "/") or (
                f.name.upper().startswith(("LICENSE", "COPYING", "NOTICE"))
                and f.suffix not in (".py", ".pyi")
            ):
                source = Path(dist.locate_file(f))
                if source.is_file():
                    target = folder / (name + "-" + str(f).replace("/", "_").replace("\\", "_"))
                    target.write_bytes(source.read_bytes())
                    notices.append(str(target.relative_to(ROOT)).replace("\\", "/"))
        records.append(
            {
                "name": name,
                "version": dist.version,
                "license": dist.metadata.get("License-Expression") or dist.metadata.get("License"),
                "home": dist.metadata.get("Home-page"),
                "notices": notices,
            }
        )
    (destination / "python-sbom.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    if python_only:
        print("Recorded", len(records), "Python components and supplied notices in", destination)
        return
    npm = []
    for lock in [ROOT / "apps/web/package-lock.json", ROOT / "package-lock.json"]:
        if not lock.exists():
            continue
        data = json.loads(lock.read_text())
        for path, pkg in data.get("packages", {}).items():
            if not path:
                continue
            source = lock.parent / path
            name = path.replace("node_modules/", "").replace("/", "_")
            notices = []
            for file in source.glob("*"):
                if file.is_file() and file.name.upper().startswith(("LICENSE", "NOTICE", "COPYING")):
                    target = folder / (name + "-" + file.name)
                    target.write_bytes(file.read_bytes())
                    notices.append(str(target.relative_to(ROOT)).replace("\\", "/"))
            npm.append(
                {
                    "name": path,
                    "version": pkg.get("version"),
                    "license": pkg.get("license"),
                    "integrity": pkg.get("integrity"),
                    "notices": notices,
                }
            )
    (destination / "npm-sbom.json").write_text(json.dumps(npm, indent=2), encoding="utf-8")
    print("Recorded", len(records), "Python and", len(npm), "npm components and supplied notices.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Repository-relative directory under manifests; default manifests")
    parser.add_argument("--python-only", action="store_true")
    args = parser.parse_args()
    main(args.output, args.python_only)
