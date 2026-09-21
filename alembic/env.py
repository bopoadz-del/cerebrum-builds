"""Alembic environment for this platform.

One place decides the database: DATABASE_URL when set (Postgres), otherwise
the SQLite file under STORAGE_PATH -- the same rule app/db.py applies at
runtime, so a migration can never run against a different database than the
app serves from.
"""

from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def sqlalchemy_url() -> str:
    """The same URL app/db.py hands the engine, driver mapping included.

    Imported rather than re-derived: a migration that runs against a
    different URL than the app serves from is exactly the divergence
    app/db.py exists to prevent, and the Postgres driver mapping
    (``postgresql://`` -> ``postgresql+psycopg://``) lives in one place.
    """
    try:
        from app.db import database_url, normalize_database_url

        url = database_url()
        if url:
            return normalize_database_url(url)
    except Exception:
        pass
    url = (os.getenv("DATABASE_URL") or "").strip()
    if url:
        return url
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return "sqlite:///" + (root / "platform.db").resolve().as_posix()


def run_migrations_offline() -> None:
    context.configure(
        url=sqlalchemy_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(sqlalchemy_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
