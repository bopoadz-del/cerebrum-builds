"""Alembic env for a generated platform.

The URL is the same one ``app/migrations.py`` computes: ``DATABASE_URL``
when the operator set it, otherwise sqlite on ``STORAGE_PATH``. Duplicated
here so a migration can run before ``app`` is imported.
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
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
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
