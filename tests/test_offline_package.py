import json
import platform
import subprocess
import sys
import zipfile
from types import SimpleNamespace

import pytest

from scripts import install_offline as installer
from scripts.offline_package import application_files, reused_wheels


def kit(tmp_path):
    (tmp_path / "application").mkdir()
    (tmp_path / "application/requirements.lock.txt").write_text("example==1\n")
    (tmp_path / "wheels").mkdir()
    with zipfile.ZipFile(tmp_path / "wheels/example-1-py3-none-any.whl", "w") as wheel:
        wheel.writestr("example.py", "pass")
    manifest = dict(
        version=2,
        kind="standalone-core",
        platform=platform.system(),
        architecture=platform.machine(),
        python=list(sys.version_info[:2]),
        files={
            p.relative_to(tmp_path).as_posix(): installer.sha(p) for p in tmp_path.rglob("*") if p.is_file()
        },
    )
    (tmp_path / "kit.json").write_text(json.dumps(manifest))
    return manifest


def test_package_integrity_and_resource_admission_precede_install(tmp_path, monkeypatch):
    kit(tmp_path)
    monkeypatch.setattr(installer.shutil, "disk_usage", lambda _: SimpleNamespace(free=20 * 1024**3))
    assert installer.verify(tmp_path)[0]["kind"] == "standalone-core"
    monkeypatch.setattr(installer.venv, "create", lambda *a, **kw: pytest.fail("must not create environment"))
    monkeypatch.setattr(installer.shutil, "disk_usage", lambda _: SimpleNamespace(free=installer.RESERVE))
    with pytest.raises(OSError, match="space"):
        installer.install(tmp_path)
    monkeypatch.setattr(installer.shutil, "disk_usage", lambda _: SimpleNamespace(free=20 * 1024**3))
    (tmp_path / "application/requirements.lock.txt").write_text("modified")
    with pytest.raises(ValueError, match="checksum"):
        installer.install(tmp_path)


def test_unlisted_files_and_existing_installation_are_rejected(tmp_path):
    kit(tmp_path)
    (tmp_path / "wheels/unlisted.whl").write_bytes(b"not trusted")
    with pytest.raises(ValueError, match="unlisted"):
        installer.verify(tmp_path)
    (tmp_path / "application/.venv").mkdir()
    with pytest.raises(ValueError, match="already exists"):
        installer.verify(tmp_path)


@pytest.mark.parametrize("name", ["../outside", "/outside", "C:/outside", "nested\\outside"])
def test_package_paths_cannot_escape(tmp_path, name):
    with pytest.raises(ValueError, match="Unsafe"):
        installer.safe_path(tmp_path, name)


def test_only_tracked_source_and_built_interface_are_packaged(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    for name in ("config/inference.toml", "config/brand.json", "services/api/example.py"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("tracked")
        subprocess.run(["git", "add", name], cwd=tmp_path, check=True)
    for name in (
        ".runtime/private.sqlite",
        ".env",
        "models/unpinned.bin",
        "docs/private.txt",
        "apps/web/dist/index.html",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("untracked")
    assert set(application_files(tmp_path)) == {
        "config/inference.toml",
        "config/brand.json",
        "services/api/example.py",
        "apps/web/dist/index.html",
    }


def test_prepared_wheels_require_matching_lock_hash_and_inventory(tmp_path):
    prior = tmp_path / "prior"
    prior.mkdir()
    kit(prior)
    source = tmp_path / "source"
    source.mkdir()
    (source / "requirements.lock.txt").write_bytes((prior / "application/requirements.lock.txt").read_bytes())
    assert len(reused_wheels(prior / "wheels", source)) == 1
    (source / "requirements.lock.txt").write_text("different==1\n")
    with pytest.raises(ValueError, match="lock"):
        reused_wheels(prior / "wheels", source)
    (source / "requirements.lock.txt").write_bytes((prior / "application/requirements.lock.txt").read_bytes())
    next((prior / "wheels").glob("*.whl")).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        reused_wheels(prior / "wheels", source)
