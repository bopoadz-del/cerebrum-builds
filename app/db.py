"""One place decides where the database lives.

This module is the platform's only connection factory. ``app/store.py`` and
``app/migrations.py`` import :func:`connect` from here rather than opening a
database themselves, so the two can never disagree about whether this
deployment is on Postgres or on the SQLite file under ``STORAGE_PATH``.

  DATABASE_URL present  -> Postgres (SQLAlchemy engine; ``postgres://`` and
                           ``postgresql://`` are normalised to the psycopg
                           driver scheme).
  DATABASE_URL absent   -> SQLite at ``<STORAGE_PATH>/platform.db``, WAL,
                           busy_timeout matched to the FastAPI sync
                           threadpool.

A DATABASE_URL that is read and then ignored is the defect this module
exists to prevent: the operator would believe they are on Postgres while the
platform wrote a SQLite file onto the container disk.

Schema is never created here. Alembic owns every table (alembic/versions/).

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

#: The single storage root. No second database, no stray sqlite file.
STORAGE_PATH_ENV = "STORAGE_PATH"
DATABASE_URL_ENV = "DATABASE_URL"
DATABASE_FILENAME = "platform.db"

#: Root used when STORAGE_PATH is unset. Every writer of deployment state --
#: the database, the RAG corpus, the mail outbox, evidence files, backups and
#: the vendored runtime's own files -- resolves through :func:`storage_root`,
#: so an unset STORAGE_PATH means one root (``./data``), never a database in
#: ``./data`` with an outbox, a corpus and an evidence directory beside it.
DEFAULT_STORAGE_ROOT = "./data"

SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0
FASTAPI_SYNC_THREADPOOL = 40


class DatabaseConfigError(RuntimeError):
    """The deployment's database settings cannot be honoured."""


def database_url() -> str:
    return (os.environ.get(DATABASE_URL_ENV) or "").strip()


def is_postgres() -> bool:
    url = database_url()
    return url.startswith("postgres://") or url.startswith("postgresql")


def dialect() -> str:
    return "postgres" if is_postgres() else "sqlite"


def storage_root() -> Path:
    """The deployment's ONE storage root, created on demand.

    Read from ``STORAGE_PATH``; unset means :data:`DEFAULT_STORAGE_ROOT`.
    This is the single place that decides, so no module can put its files
    beside the root instead of inside it. Returns an absolute path so a
    process that changes directory later still writes where it started.
    """
    root = Path(os.environ.get(STORAGE_PATH_ENV) or DEFAULT_STORAGE_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def db_path() -> Path:
    """The SQLite file this deployment would use. Unused on Postgres."""
    return storage_root() / DATABASE_FILENAME


def _normalised_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_ENGINE: Any = None


def engine() -> Any:
    """The process-wide SQLAlchemy engine. Postgres only."""
    global _ENGINE
    if _ENGINE is None:
        try:
            from sqlalchemy import create_engine
        except ImportError as exc:  # pragma: no cover - declared dependency
            raise DatabaseConfigError(
                "DATABASE_URL is set but SQLAlchemy is not installed"
            ) from exc
        _ENGINE = create_engine(
            _normalised_url(database_url()),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            future=True,
        )
    return _ENGINE


class PostgresCursor:
    """A DBAPI-shaped cursor over a SQLAlchemy result."""

    def __init__(self, result: Any, lastrowid: Any = None, rowcount: int = 0):
        self._result = result
        self._rows: List[Any] | None = None
        self.lastrowid = lastrowid
        self.rowcount = rowcount

    def _materialise(self) -> List[Any]:
        if self._rows is None:
            self._rows = list(self._result.fetchall()) if self._result is not None else []
        return self._rows

    def fetchone(self) -> Any:
        rows = self._materialise()
        return rows[0] if rows else None

    def fetchall(self) -> List[Any]:
        return list(self._materialise())

    def __iter__(self):
        return iter(self._materialise())


class PostgresConnection:
    """SQLite-flavoured facade over a SQLAlchemy Postgres connection.

    The rest of the platform writes ``?`` placeholders and reads rows by
    name (or by index, for ``COUNT(*)``); this adapter keeps that true on
    Postgres instead of forking every call site.
    """

    def __init__(self) -> None:
        self._conn = engine().connect()

    @staticmethod
    def _translate(sql: str) -> str:
        """``?`` placeholders become SQLAlchemy ``:pN`` bind names."""
        return _named_statement(str(sql))

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> PostgresCursor:
        from sqlalchemy import text as _text

        statement = self._translate(str(sql))
        params = tuple(params or ())
        upper = statement.lstrip().upper()
        if upper.startswith("INSERT"):
            statement = statement.rstrip().rstrip(";") + " RETURNING id"
            result = self._conn.execute(_text(statement), dict(_as_named(params)))
            rows = list(result.fetchall())
            self._conn.commit()
            new_id = rows[0][0] if rows else None
            return PostgresCursor(None, lastrowid=new_id, rowcount=len(rows))
        result = self._conn.execute(_text(statement), dict(_as_named(params)))
        if upper.startswith(("SELECT", "WITH")):
            return PostgresCursor(result)
        self._conn.commit()
        return PostgresCursor(None, rowcount=result.rowcount or 0)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def _as_named(params: Sequence[Any]) -> Iterable[Tuple[str, Any]]:
    for index, value in enumerate(params):
        yield "p%d" % index, value


def _named_statement(sql: str) -> str:
    """Rewrite ``?`` placeholders to ``:p0, :p1`` for SQLAlchemy text()."""
    out: List[str] = []
    index = 0
    in_string = False
    quote = ""
    for char in str(sql):
        if in_string:
            out.append(char)
            if char == quote:
                in_string = False
            continue
        if char in ("'", '"'):
            in_string, quote = True, char
            out.append(char)
        elif char == "?":
            out.append(":p%d" % index)
            index += 1
        else:
            out.append(char)
    return "".join(out)


def connect() -> Any:
    """Open a connection to this deployment's one database."""
    if is_postgres():
        return PostgresConnection()
    conn = sqlite3.connect(
        str(db_path()),
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


def describe() -> Dict[str, Any]:
    """What this process is actually connected to, for /health and logs."""
    if is_postgres():
        host = ""
        raw = database_url()
        if "@" in raw:
            host = raw.split("@", 1)[1].split("/", 1)[0]
        return {"dialect": "postgres", "host": host, "storage_path": None}
    return {
        "dialect": "sqlite",
        "host": None,
        "storage_path": str(db_path()),
        "journal_mode": "WAL",
    }
