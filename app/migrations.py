"""Alembic head / targeted upgrades. connect() does not apply schema."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config

from app.store import db_path, reset_connection, storage_path

REV_V1 = "0001_baseline"
REV_V2 = "0002_lifecycle_audit"
HEAD = REV_V2


def _config() -> Config:
    ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(ini))
    storage_path().mkdir(parents=True, exist_ok=True)
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path()}")
    return cfg


def current_revision() -> Optional[str]:
    reset_connection()
    conn = None
    try:
        from app.store import connect

        conn = connect()
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        if conn is not None:
            conn.close()


def upgrade_head() -> Optional[str]:
    reset_connection()
    command.upgrade(_config(), "head")
    reset_connection()
    return current_revision()


def upgrade_to(revision: str) -> Optional[str]:
    reset_connection()
    command.upgrade(_config(), revision)
    reset_connection()
    return current_revision()


def downgrade(revision: str) -> Optional[str]:
    reset_connection()
    command.downgrade(_config(), revision)
    reset_connection()
    return current_revision()
