import smtplib

import pytest

from services.api import config
from services.api.dates import resolve
from services.api.db import canonical, migrate, transaction
from scripts.mom import backup, restore
from services.worker.supervisor import deliver_one


def test_backup_restore_database_and_audio(tmp_path, monkeypatch):
    original = tmp_path / "original"
    monkeypatch.setattr(config, "DATA", original)
    migrate()
    (original / "audio/ack.pcm").write_bytes(b"acknowledged")
    with transaction() as c:
        c.execute("INSERT INTO users VALUES('u','secretary','hash','secretary','en')")
    backup(tmp_path / "backup")
    monkeypatch.setattr(config, "DATA", tmp_path / "restored")
    restore(tmp_path / "backup")
    with transaction() as c:
        assert c.execute("SELECT name FROM users").fetchone()[0] == "secretary"
    assert (config.DATA / "audio/ack.pcm").read_bytes() == b"acknowledged"


def test_backup_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    migrate()
    with pytest.raises(SystemExit):
        backup(config.DATA)


def test_stop_uses_stable_identity_even_if_legacy_timestamp_drifts(tmp_path, monkeypatch):
    import json
    import subprocess
    import sys
    from scripts.mom import stop
    from services.worker.process_identity import identity

    monkeypatch.setattr(config, "DATA", tmp_path)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        (tmp_path / "processes.json").write_text(
            json.dumps(
                [{"pid": child.pid, "created": 0, "identity": identity(child.pid), "name": "test-child"}]
            )
        )
        stop()
        assert child.wait(timeout=5) is not None
        assert not (tmp_path / "processes.json").exists()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


def test_stop_does_not_kill_a_reused_pid(tmp_path, monkeypatch):
    import json
    import subprocess
    import sys
    from scripts.mom import stop

    monkeypatch.setattr(config, "DATA", tmp_path)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        (tmp_path / "processes.json").write_text(
            json.dumps(
                [
                    {
                        "pid": child.pid,
                        "created": 0,
                        "identity": {"kind": "different", "value": "old-process"},
                        "name": "test-child",
                    }
                ]
            )
        )
        stop()
        assert child.poll() is None
    finally:
        child.kill()
        child.wait()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("30 septembrie", "2026-09-30"),
        ("September 30th", "2026-09-30"),
        ("30 сентября", "2026-09-30"),
        ("03/04", None),
        ("tomorrow", "2026-09-26"),
        ("31 September", None),
    ],
)
def test_conservative_dates(raw, expected):
    assert resolve(raw, "2026-09-25") == expected


def test_smtp_timeout_does_not_automatically_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    migrate()
    with transaction() as c:
        c.execute(
            "INSERT INTO meetings VALUES('m','test','2026-09-25','Europe/Chisinau','en','Administrative',1,'ready',0)"
        )
        c.execute(
            "INSERT INTO snapshots VALUES('s','m',1,?,'hash','<p>synthetic</p>',0)",
            (canonical({"meeting": {"title": "Synthetic"}}),),
        )
        c.execute(
            "INSERT INTO outbox(id,snapshot_id,addresses,recipient_hash,state,message_id,created) VALUES('o','s','[\"x@secure-mom.test\"]','hash','queued','<o@test>',0)"
        )

    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def send_message(self, msg):
            raise TimeoutError("after DATA")

    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    assert deliver_one()
    assert not deliver_one()
    with transaction() as c:
        row = c.execute("SELECT state,attempt FROM outbox").fetchone()
        assert tuple(row) == ("uncertain", 1)


@pytest.mark.parametrize(
    "tls,expected", [("starttls", "smtp_accepted"), ("none", "failed"), ("ssl", "smtp_accepted")]
)
def test_internal_smtp_requires_verified_tls_before_auth(tmp_path, monkeypatch, tls, expected):
    import ssl

    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setenv("MOM_SMTP_HOST", "mail.internal.example")
    monkeypatch.setenv("MOM_SMTP_TLS", tls)
    monkeypatch.setenv("MOM_SMTP_USER", "synthetic-user")
    monkeypatch.setenv("MOM_SMTP_PASSWORD", "synthetic-password")
    migrate()
    with transaction() as c:
        c.execute(
            "INSERT INTO meetings VALUES('m','test','2026-09-25','Europe/Chisinau','en','Administrative',1,'ready',0)"
        )
        c.execute(
            "INSERT INTO snapshots VALUES('s','m',1,?,'hash','<p>synthetic</p>',0)",
            (canonical({"meeting": {"title": "Synthetic"}}),),
        )
        c.execute(
            "INSERT INTO outbox(id,snapshot_id,addresses,recipient_hash,state,message_id,created) VALUES('o','s','[\"x@secure-mom.test\"]','hash','queued','<o@test>',0)"
        )
    calls = []

    class SMTP:
        def __init__(self, *args, **kwargs):
            calls.append("connect")
            self.secure = "context" in kwargs
            if self.secure:
                self.check_context(kwargs["context"])

        def check_context(self, context):
            assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ehlo(self):
            calls.append("ehlo")

        def starttls(self, context):
            self.check_context(context)
            self.secure = True
            calls.append("tls")

        def login(self, user, password):
            assert self.secure
            assert (user, password) == ("synthetic-user", "synthetic-password")
            calls.append("auth")

        def send_message(self, msg):
            assert self.secure and calls[-1] == "auth"
            assert msg["Message-ID"] == "<o@test>"
            calls.append("send")
            return {}

    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP)
    assert deliver_one()
    with transaction() as c:
        assert c.execute("SELECT state FROM outbox").fetchone()[0] == expected
    assert calls == (
        []
        if tls == "none"
        else ["connect", "ehlo", "tls", "ehlo", "auth", "send"]
        if tls == "starttls"
        else ["connect", "auth", "send"]
    )


def test_corrupt_backup_and_nonempty_restore_are_rejected_before_writing(tmp_path, monkeypatch):
    original = tmp_path / "original"
    monkeypatch.setattr(config, "DATA", original)
    migrate()
    (original / "audio/ack.pcm").write_bytes(b"source")
    saved = tmp_path / "backup"
    backup(saved)
    (saved / "audio/ack.pcm").write_bytes(b"corrupted")
    restored = tmp_path / "restored"
    monkeypatch.setattr(config, "DATA", restored)
    with pytest.raises(SystemExit, match="checksum mismatch"):
        restore(saved)
    assert not restored.exists()
    restored.mkdir()
    (restored / "keep.txt").write_text("existing")
    with pytest.raises(SystemExit, match="new empty"):
        restore(saved)
    assert (restored / "keep.txt").read_text() == "existing"


def test_backup_rejects_nested_destination(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    migrate()
    with pytest.raises(SystemExit, match="outside"):
        backup(config.DATA / "audio/nested-backup")
