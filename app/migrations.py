"""Apply and roll back Alembic revisions for this platform.

Deploy (``scripts/entrypoint.sh``) and the FastAPI lifespan both call
``upgrade_head()`` against the configured database: DATABASE_URL when set,
otherwise the SQLite file under STORAGE_PATH (app/db.py decides). A migration
that fails refuses boot -- a platform serving requests against a schema it
never applied is worse than one that does not start.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config

from app.db import connect, is_postgres

ROOT = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    return cfg


def upgrade_head() -> Optional[str]:
    command.upgrade(alembic_config(), "head")
    return current_revision()


def upgrade_to(revision: str) -> Optional[str]:
    command.upgrade(alembic_config(), revision)
    return current_revision()


def downgrade(revision: str) -> Optional[str]:
    command.downgrade(alembic_config(), revision)
    return current_revision()


def current_revision() -> Optional[str]:
    """The revision the database is stamped at, or None before the first one."""
    conn = connect()
    try:
        try:
            cur = conn.execute("SELECT version_num FROM alembic_version")
            rows = cur.fetchall()
        except Exception:
            return None
        if not rows:
            return None
        row = rows[0]
        mapping = getattr(row, "_mapping", None)
        if mapping is not None:
            return str(mapping["version_num"])
        return str(row[0])
    finally:
        conn.close()


def head_revision() -> Optional[str]:
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def backend() -> str:
    return "postgres" if is_postgres() else "sqlite"
