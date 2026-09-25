import hashlib
import json
import platform
import tarfile
import zipfile

import httpx

from services.api.config import ROOT


def prepare():
    windows = platform.system() == "Windows"
    folder = ROOT / ".runtime/tools"
    folder.mkdir(parents=True, exist_ok=True)
    if windows:
        assets = [
            ("llama", "https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-win-cuda-12.4-x64.zip"),
            ("llama", "https://github.com/ggml-org/llama.cpp/releases/download/b11146/cudart-llama-bin-win-cuda-12.4-x64.zip"),
            ("mailpit", "https://github.com/axllent/mailpit/releases/download/v1.31.2/mailpit-windows-amd64.zip"),
        ]
    else:
        assets = [("mailpit", "https://github.com/axllent/mailpit/releases/download/v1.31.2/mailpit-linux-amd64.tar.gz")]
    records = []
    for name, url in assets:
        target = folder / url.rsplit('/', 1)[1]
        if not target.exists():
            print("Downloading", target.name, flush=True)
            with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
                r.raise_for_status()
                with target.open('wb') as f:
                    for chunk in r.iter_bytes(1024 * 1024):
                        f.write(chunk)
        h = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
        dest = folder / name
        dest.mkdir(exist_ok=True)
        if target.suffix == '.zip':
            with zipfile.ZipFile(target) as z:
                z.extractall(dest)
        else:
            with tarfile.open(target) as t:
                t.extractall(dest, filter='data')
        records.append(dict(url=url, sha256=h))
    (ROOT / 'manifests/tools.lock.json').write_text(json.dumps(records, indent=2))


if __name__ == '__main__':
    prepare()
