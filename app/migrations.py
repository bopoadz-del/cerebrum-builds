"""Apply and roll back Alembic revisions for this platform.

Deploy (``scripts/entrypoint.sh``) and the FastAPI lifespan both call
``upgrade_head()`` against the configured database: DATABASE_URL when set,
otherwise the SQLite file under STORAGE_PATH (app/db.py decides). A migration
that fails refuses boot -- a platform serving requests against a schema it
never applied is worse than one that does not start.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

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


#: The head revision is fixed for the life of the process: it is read from the
#: revision files on disk, and a change there means a new deploy (a restart).
#: /health asks for it on every probe, and rebuilding Alembic's ScriptDirectory
#: each time cost ~1.5ms of the probe's budget under load. Cached once, with
#: the database's own stamped revision still read live on every request.
_HEAD_CACHE: Dict[str, Optional[str]] = {}


def head_revision() -> Optional[str]:
    if "head" in _HEAD_CACHE:
        return _HEAD_CACHE["head"]
    from alembic.script import ScriptDirectory

    _HEAD_CACHE["head"] = ScriptDirectory.from_config(alembic_config()).get_current_head()
    return _HEAD_CACHE["head"]


def backend() -> str:
    return "postgres" if is_postgres() else "sqlite"
