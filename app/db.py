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


def is_postgres() -> bool:
    return bool(database_url())


def sqlite_path() -> Path:
    root = Path(os.environ.get("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "platform.db"


#: The driver this platform declares (``psycopg[binary]>=3.1``). A plain
#: ``postgres://`` / ``postgresql://`` URL names no driver, and SQLAlchemy then
#: reaches for psycopg2, which is not a dependency here -- a deployment would
#: fail to boot with a ModuleNotFoundError instead of connecting. The plain
#: schemes are mapped onto the installed v3 driver; an explicit ``+driver`` the
#: operator wrote is left exactly as written.
POSTGRES_DRIVER = "psycopg"


def sqlalchemy_url(url: str) -> str:
    """DATABASE_URL, pointed at a driver that is actually installed."""
    for scheme in ("postgres://", "postgresql://"):
        if url.startswith(scheme):
            return f"postgresql+{POSTGRES_DRIVER}://" + url[len(scheme):]
    return url


def engine() -> Any:
    """The SQLAlchemy engine for DATABASE_URL. Raises when there is none.

    Refuses at boot rather than degrading: a platform that cannot honour the
    variable must say so with the variable's name in the message, not fall
    back to SQLite and let the operator believe otherwise.
    """
    global _ENGINE
    url = database_url()
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
                "platform cannot honour it. Install sqlalchemy and the driver "
                f"it declares ({POSTGRES_DRIVER}[binary]) or unset DATABASE_URL."
            ) from exc
        _ENGINE = create_engine(sqlalchemy_url(url), pool_pre_ping=True, future=True)
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
