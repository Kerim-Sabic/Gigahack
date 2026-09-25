"""Collect installed package provenance and preserve supplied license notices."""

import importlib.metadata as md
import json
from pathlib import Path

from services.api.config import ROOT


def main():
    folder = ROOT / "manifests/licenses"
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for dist in md.distributions():
        name = dist.metadata["Name"]
        notices = []
        for f in dist.files or []:
            if "__pycache__" in f.parts or f.suffix == ".pyc":
                continue
            if "dist-info/licenses/" in str(f) or f.name.upper() in (
                "LICENSE",
                "LICENSE.TXT",
                "COPYING",
                "NOTICE",
            ):
                source = Path(dist.locate_file(f))
                if source.is_file() and source.stat().st_size < 200000:
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
    (ROOT / "manifests/python-sbom.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
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
    (ROOT / "manifests/npm-sbom.json").write_text(json.dumps(npm, indent=2), encoding="utf-8")
    print("Recorded", len(records), "Python and", len(npm), "npm components and supplied notices.")


if __name__ == "__main__":
    main()
