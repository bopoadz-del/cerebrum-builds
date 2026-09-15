"""Alembic helpers. connect() does not create domain tables — this module does."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.store import db_path, reset_connection

HEAD = "0002_lifecycle_audit"
ROOT = Path(__file__).resolve().parents[1]


def _config() -> Config:
    ini = ROOT / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path()}")
    return cfg


def current_revision() -> str | None:
    path = db_path()
    if not path.is_file():
        return None
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ).fetchone()
        if row is None:
            return None
        current = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return current[0] if current else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def upgrade_head() -> str | None:
    reset_connection()
    command.upgrade(_config(), "head")
    reset_connection()
    return current_revision()


def upgrade_to(revision: str) -> str | None:
    reset_connection()
    command.upgrade(_config(), revision)
    reset_connection()
    return current_revision()


def downgrade(revision: str) -> str | None:
    reset_connection()
    command.downgrade(_config(), revision)
    reset_connection()
    return current_revision()


def head_revision() -> str:
    script = ScriptDirectory.from_config(_config())
    return script.get_current_head() or HEAD
