"""Online-only preparation. Never imported by startup or inference."""
import hashlib
import json

from huggingface_hub import HfApi, snapshot_download

from services.api.config import MODELS, ROOT


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def prepare():
    lockpath = ROOT / "manifests/models.lock.json"
    previous = json.loads(lockpath.read_text()) if lockpath.exists() else {}
    specs = [
        ("whisper", "Systran/faster-whisper-large-v3", ["*.json", "*.bin", "*.txt", "README.md"], "MIT"),
        ("qwen", "unsloth/Qwen3.5-4B-GGUF", ["*Q4_K_M.gguf", "README.md"], "Apache-2.0"),
    ]
    manifest = {}
    for name, repo, patterns, license_name in specs:
        revision = previous.get(name, {}).get("revision") or HfApi().model_info(repo).sha
        print(f"Preparing {name} at {revision}", flush=True)
        folder = MODELS / name
        snapshot_download(repo, revision=revision, allow_patterns=patterns, local_dir=folder)
        files = {str(p.relative_to(folder)).replace('\\', '/'): digest(p)
                 for p in folder.rglob('*') if p.is_file() and '.cache' not in p.parts}
        manifest[name] = dict(repo=repo, revision=revision, license=license_name, files=files,
                              qualification="not measured")
        lockpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Prepared immutable model manifest. Runtime performs no downloads.")


if __name__ == "__main__":
    prepare()
