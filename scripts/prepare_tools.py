import hashlib
import json
import platform
import tarfile
import zipfile

import httpx

from services.api.config import ROOT


def prepare(mail_only=False):
    windows = platform.system() == "Windows"
    folder = ROOT / ".runtime/tools"
    folder.mkdir(parents=True, exist_ok=True)
    if windows:
        assets = [
            (
                "llama",
                "https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-win-cuda-12.4-x64.zip",
            ),
            (
                "llama",
                "https://github.com/ggml-org/llama.cpp/releases/download/b11146/cudart-llama-bin-win-cuda-12.4-x64.zip",
            ),
            (
                "mailpit",
                "https://github.com/axllent/mailpit/releases/download/v1.31.2/mailpit-windows-amd64.zip",
            ),
        ]
    else:
        assets = [
            (
                "llama",
                "https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-ubuntu-cuda-12.8-x64.tar.gz",
            ),
            (
                "llama",
                "https://github.com/ggml-org/llama.cpp/releases/download/b11146/cudart-llama-b11146-bin-ubuntu-cuda-12.8-x64.tar.gz",
            ),
            (
                "mailpit",
                "https://github.com/axllent/mailpit/releases/download/v1.31.2/mailpit-linux-amd64.tar.gz",
            ),
        ]
    if mail_only:
        assets = [asset for asset in assets if asset[0] == "mailpit"]
    records = []
    manifest = ROOT / "manifests/tools.lock.json"
    existing = json.loads(manifest.read_text()) if manifest.exists() else []
    pinned = {r["url"]: r["sha256"] for r in existing}
    files_manifest = ROOT / "manifests/tool-files.lock.json"
    all_files = json.loads(files_manifest.read_text()) if files_manifest.exists() else {}
    platform_files = dict(all_files.get(platform.system(), {}))
    for name, url in assets:
        target = folder / url.rsplit("/", 1)[1]
        if not target.exists():
            print("Downloading", target.name, flush=True)
            with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
                r.raise_for_status()
                partial = target.with_suffix(target.suffix + ".partial")
                with partial.open("wb") as f:
                    for chunk in r.iter_bytes(1024 * 1024):
                        f.write(chunk)
                partial.replace(target)
        with target.open("rb") as f:
            h = hashlib.file_digest(f, "sha256").hexdigest()
        if url in pinned and h != pinned[url]:
            raise RuntimeError(f"Pinned tool checksum mismatch: {target.name}; archive was not extracted")
        dest = folder / name
        dest.mkdir(exist_ok=True)
        if target.suffix == ".zip":
            with zipfile.ZipFile(target) as z:
                z.extractall(dest)
                members = [info.filename for info in z.infolist() if not info.is_dir()]
        else:
            with tarfile.open(target) as t:
                t.extractall(dest, filter="data")
                members = [
                    info.name for info in t.getmembers() if info.isfile() or info.issym() or info.islnk()
                ]
        for member in members:
            path = dest / member
            if not path.resolve().is_relative_to(dest.resolve()) or not path.is_file():
                raise RuntimeError("Extracted tool member escaped its destination or is missing")
            relative = path.relative_to(folder).as_posix()
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if relative in platform_files and platform_files[relative] != digest:
                raise RuntimeError("Extracted tool differs from its pinned file checksum")
            platform_files[relative] = digest
        records.append(dict(url=url, sha256=h))
    combined = {r["url"]: r for r in existing}
    combined.update({r["url"]: r for r in records})
    manifest.write_text(json.dumps(list(combined.values()), indent=2))
    all_files[platform.system()] = platform_files
    partial = files_manifest.with_suffix(".partial")
    partial.write_text(json.dumps(all_files, indent=2), encoding="utf-8")
    partial.replace(files_manifest)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mail-only", action="store_true")
    prepare(parser.parse_args().mail_only)
