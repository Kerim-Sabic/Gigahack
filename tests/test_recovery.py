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
