"""DATABASE_URL is honoured, never read and ignored.

The failure this guards against: an operator sets DATABASE_URL, the platform
accepts it without complaint, and writes a SQLite file onto the container
disk anyway. One place decides the backend (app/db.py) and app/store.py takes
its connection from there.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_store_takes_its_connection_from_app_db():
    source = (ROOT / "app" / "store.py").read_text(encoding="utf-8")
    assert "from app.db import" in source
    assert "sqlite3.connect(" not in source
    assert "create_engine(" not in source


def test_app_db_is_the_only_place_that_reads_database_url():
    db_source = (ROOT / "app" / "db.py").read_text(encoding="utf-8")
    assert "DATABASE_URL" in db_source
    elsewhere = []
    for path in (ROOT / "app").rglob("*.py"):
        if path.name == "db.py" or "factory" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "DATABASE_URL" in text and "app.db" not in text and path.name != "migrations.py":
            elsewhere.append(str(path.relative_to(ROOT)))
    assert not elsewhere, f"DATABASE_URL read outside app/db.py: {elsewhere}"


def test_a_set_database_url_switches_the_backend(monkeypatch):
    import app.db as db

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@127.0.0.1:1/callops")
    importlib.reload(db)
    import app.store as store

    importlib.reload(store)
    assert db.is_postgres() is True
    assert store.backend() == "postgres"
    # The engine is for Postgres; a failed connect must not fall back to sqlite.
    with pytest.raises(Exception):
        store.connect()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    importlib.reload(db)
    importlib.reload(store)
    assert db.is_postgres() is False
    assert store.backend() == "sqlite"


def test_a_plain_postgres_url_is_mapped_onto_the_declared_driver():
    """DATABASE_URL is honoured, not quietly answered by SQLite.

    ``postgres://`` names no driver, and SQLAlchemy's fallback (psycopg2) is
    not a dependency of this platform: an operator who sets DATABASE_URL would
    meet ModuleNotFoundError instead of a connection. The plain schemes are
    mapped onto the driver requirements.txt declares.
    """
    from app import db

    assert db.POSTGRES_DRIVER == "psycopg"
    assert (
        db.sqlalchemy_url("postgres://u:p@db:5432/callops")
        == "postgresql+psycopg://u:p@db:5432/callops"
    )
    assert (
        db.sqlalchemy_url("postgresql://u:p@db:5432/callops")
        == "postgresql+psycopg://u:p@db:5432/callops"
    )
    # an explicit driver the operator wrote is left exactly as written
    written = "postgresql+psycopg2://u:p@db:5432/callops"
    assert db.sqlalchemy_url(written) == written
    # and a SQLite setting is not a Postgres URL
    assert db.sqlalchemy_url("sqlite:///./data/platform.db") == "sqlite:///./data/platform.db"
