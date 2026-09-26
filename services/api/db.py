"""Short, explicit SQLite transactions; WAL and checked meeting references."""

import contextlib
import json
import sqlite3
import time
import uuid

from . import config


def uid():
    return str(uuid.uuid4())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


MIGRATIONS = __import__("pathlib").Path(__file__).parent / "migrations"


@contextlib.contextmanager
def transaction():
    config.init_dirs()
    conn = sqlite3.connect(config.DATA / "app.sqlite", timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate():
    config.init_dirs()
    with sqlite3.connect(config.DATA / "app.sqlite") as c:
        c.execute("PRAGMA journal_mode=WAL")
        exists = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone()
        version = (
            c.execute("SELECT COALESCE(MAX(version),0) FROM schema_version").fetchone()[0] if exists else 0
        )
        if version > 6:
            raise RuntimeError("Database schema is newer than this application; refusing downgrade")
        for path in sorted(MIGRATIONS.glob("*.sql")):
            number = int(path.name.split("_")[0])
            if number > version:
                c.executescript("BEGIN IMMEDIATE;\n" + path.read_text(encoding="utf-8") + "\nCOMMIT;")


def audit(c, meeting, actor, kind, payload=None):
    c.execute(
        "INSERT INTO audit(meeting_id,actor,kind,payload,created) VALUES(?,?,?,?,?)",
        (meeting, actor, kind, canonical(payload or {}), time.time()),
    )
