"""Alembic wrappers. connect() does not apply schema — these commands do."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.store import db_path, reset_connection


def _config() -> Config:
    ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path()}")
    return cfg


def current_revision() -> str | None:
    engine = create_engine(f"sqlite:///{db_path()}")
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def head_revision() -> str | None:
    script = ScriptDirectory.from_config(_config())
    return script.get_current_head()


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
