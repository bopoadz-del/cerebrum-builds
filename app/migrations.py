"""Apply and roll back Alembic revisions for this platform.

Deploy (``scripts/entrypoint.sh``) and the FastAPI lifespan both call
``upgrade_head()`` against the one storage root. Failure refuses boot: a
container serving traffic against a schema it never migrated is worse than
one that never started.

The URL comes from the same decision ``app.db`` makes — ``DATABASE_URL``
when the operator set it, otherwise sqlite on ``STORAGE_PATH`` — so the
migration and the connection can never disagree about which database the
platform is on.
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.store import connect, db_path

ROOT = Path(__file__).resolve().parents[1]


def database_url() -> str:
    return (os.environ.get("DATABASE_URL") or "").strip()


def sqlalchemy_url() -> str:
    url = database_url()
    if url:
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url
    target = db_path().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    return "sqlite:///" + target.as_posix()


def alembic_config() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", sqlalchemy_url())
    return cfg


def upgrade_head() -> str | None:
    command.upgrade(alembic_config(), "head")
    return current_revision()


def upgrade_to(revision: str) -> str | None:
    command.upgrade(alembic_config(), revision)
    return current_revision()


def downgrade(revision: str) -> str | None:
    command.downgrade(alembic_config(), revision)
    return current_revision()


def current_revision() -> str | None:
    """The revision this database is stamped at, or None."""
    try:
        conn = connect()
    except Exception:
        return None
    try:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return str(row[0]) if row else None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def head_revision() -> str | None:
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(alembic_config()).get_current_head()
