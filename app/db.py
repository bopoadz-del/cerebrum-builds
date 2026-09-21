"""Where this platform's database connection comes from.

Written by the factory. DATABASE_URL set means Postgres; absent means a
SQLite file under STORAGE_PATH for development. One place decides, so the
two cannot disagree.

app/store.py MUST obtain its connection from here and MUST NOT open its own
database. A DATABASE_URL that is read and then ignored is the failure this
module exists to prevent: the operator believes they are on Postgres while
the platform writes a SQLite file onto the container disk.

    from app.db import connect, engine, is_postgres

    with connect() as conn:
        ...
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

#: Matched to the FastAPI sync threadpool: one writer, readers proceed.
SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0

_ENGINE: Optional[Any] = None


def database_url() -> str:
    """The operator's choice, or empty for the SQLite development default."""
    return (os.environ.get("DATABASE_URL") or "").strip()


def normalize_database_url(url: str) -> str:
    """Pin DATABASE_URL to the driver this platform actually installs.

    SQLAlchemy reads a bare ``postgresql://`` URL as "use psycopg2", which is
    not a dependency here: the operator sets DATABASE_URL, the platform
    accepts it and then dies at boot on a missing driver -- or worse, a
    deployment that never boots Postgres quietly proves nothing. Mapping the
    scheme onto psycopg (v3) is what makes the variable honourable; a URL
    that already names a driver is left exactly as the operator wrote it.
    """
    text = (url or "").strip()
    low = text.lower()
    for scheme in ("postgresql", "postgres"):
        for separator in ("://", ":"):
            prefix = scheme + separator
            if low.startswith(prefix) and "+" not in low.split("://", 1)[0]:
                return "postgresql+psycopg://" + text[len(prefix) :]
    return text


def sqlalchemy_url() -> str:
    """The URL migrations and the engine both use -- one normalisation."""
    return normalize_database_url(database_url())


def is_postgres() -> bool:
    return bool(database_url())


def sqlite_path() -> Path:
    root = Path(os.environ.get("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "platform.db"


def engine() -> Any:
    """The SQLAlchemy engine for DATABASE_URL. Raises when there is none.

    Refuses at boot rather than degrading: a platform that cannot honour the
    variable must say so with the variable's name in the message, not fall
    back to SQLite and let the operator believe otherwise.
    """
    global _ENGINE
    url = sqlalchemy_url()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set; this platform is on SQLite at "
            f"{sqlite_path()}. Use connect() for a connection that works on "
            "either backend."
        )
    if _ENGINE is None:
        try:
            from sqlalchemy import create_engine
        except ImportError as exc:  # pragma: no cover - deploy-time failure
            raise RuntimeError(
                "DATABASE_URL is set but SQLAlchemy is not installed, so this "
                "platform cannot honour it. Install sqlalchemy and a driver "
                "(psycopg[binary]) or unset DATABASE_URL."
            ) from exc
        _ENGINE = create_engine(url, pool_pre_ping=True, future=True)
    return _ENGINE


def connect() -> Any:
    """A live connection on whichever backend is configured.

    Postgres: a SQLAlchemy connection. SQLite: a stdlib sqlite3 connection
    with WAL and a busy timeout. Both are context managers and both are
    closed by the caller.
    """
    if is_postgres():
        return engine().connect()
    conn = sqlite3.connect(
        str(sqlite_path()),
        timeout=SQLITE_CONNECT_TIMEOUT_S,
        check_same_thread=False,
        isolation_level="DEFERRED",
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def backend_name() -> str:
    """What /health and the acceptance harness report."""
    return "postgres" if is_postgres() else "sqlite"
