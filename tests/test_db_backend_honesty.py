"""The database claim the operator reads is the one the platform can honour.

Written by the factory WRITER role (codewhale exec)

Three claims are checked here, each of them a way this class of platform has
been shipped broken:

* ``DATABASE_URL`` is read *and* dialable -- the scheme the operator writes
  (``postgres://`` / ``postgresql://``) is pinned onto the driver this
  platform actually installs, so "we support Postgres" is not a scheme
  nothing can connect with;
* there is exactly one place that decides the backend, and ``app/store.py``
  takes its connection from it rather than opening its own database beside
  it;
* the migration runner reads the same normalised URL, so a deploy cannot
  migrate one database and serve from another.
"""

from __future__ import annotations

from pathlib import Path

from app.db import database_url, normalize_database_url, sqlalchemy_url

ROOT = Path(__file__).resolve().parents[1]


def test_bare_postgres_scheme_is_pinned_to_the_installed_driver():
    assert (
        normalize_database_url("postgres://user:pw@db.internal:5432/hotel")
        == "postgresql+psycopg://user:pw@db.internal:5432/hotel"
    )
    assert (
        normalize_database_url("postgresql://user:pw@db.internal/hotel")
        == "postgresql+psycopg://user:pw@db.internal/hotel"
    )


def test_a_driver_qualified_url_is_left_exactly_as_the_operator_wrote_it():
    written = "postgresql+psycopg://user:pw@db.internal/hotel"
    assert normalize_database_url(written) == written
    assert normalize_database_url("sqlite:////tmp/other.db") == "sqlite:////tmp/other.db"
    assert normalize_database_url("") == ""


def test_the_postgres_driver_is_a_declared_dependency():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "psycopg" in requirements, (
        "app/db.py pins DATABASE_URL to psycopg; the dependency must be declared"
    )


def test_sqlalchemy_url_follows_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url() == ""
    assert sqlalchemy_url() == ""
    monkeypatch.setenv("DATABASE_URL", "postgres://u@h/db")
    assert sqlalchemy_url() == "postgresql+psycopg://u@h/db"


def test_migrations_read_the_same_url_as_the_store():
    env = (ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
    assert "normalize_database_url" in env, (
        "alembic/env.py must normalise through app.db, not its own copy"
    )
    store = (ROOT / "app" / "store.py").read_text(encoding="utf-8")
    assert "from app.db import" in store, "app/store.py must take its connection from app.db"
    assert "sqlite3.connect(" not in store, "app/store.py must not open its own database"
    assert "create_engine(" not in store, "app/store.py must not build its own engine"
