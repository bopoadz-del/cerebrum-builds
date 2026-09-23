"""Fail-closed process health for Render and the local drill.

A 200 means this process is serving, STORAGE_PATH is a writable
persistent disk, the database the store actually uses answers, and
Alembic is at head. Anything else is 503. Unconditional ok:true is F1
and is forbidden here.

SQLite (no ``DATABASE_URL``): the database is ``<STORAGE_PATH>/platform.db``.
Postgres (``DATABASE_URL`` set): the connection comes from ``app.db``,
exactly as ``app/store.py`` takes it -- the two must never disagree about
which database is being served.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi.responses import JSONResponse

from app.revision import current_app_mark, current_app_revision


def _storage_root() -> Path | None:
    # An empty value is "the operator set nothing", the same thing
    # app/config.py means by it — the two must not disagree about the disk.
    raw = (os.getenv("STORAGE_PATH") or "").strip()
    if not raw:
        return None
    return Path(raw)


def evaluate_health() -> Tuple[int, Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    checks.append(
        {
            "name": "process",
            "ok": True,
            "detail": f"pid={os.getpid()}",
        }
    )

    storage = _storage_root()
    if storage is None:
        disk_ok, disk_detail = False, "STORAGE_PATH unset"
    elif not storage.exists():
        disk_ok, disk_detail = False, f"missing {storage}"
    elif not os.access(storage, os.R_OK | os.W_OK):
        disk_ok, disk_detail = False, f"not writable {storage}"
    else:
        disk_ok, disk_detail = True, str(storage)
    checks.append(
        {"name": "persistent_disk", "ok": disk_ok, "detail": disk_detail}
    )

    db_ok = False
    db_detail = "not checked"
    db_path = (storage / "platform.db") if storage is not None else None
    postgres = False
    try:
        from app.db import is_postgres, connect as db_connect

        postgres = bool(is_postgres())
    except Exception:  # noqa: BLE001 -- health must not raise
        postgres = False
    if postgres:
        # The operator set DATABASE_URL, so the database is Postgres and
        # there is no platform.db file to stat -- requiring one made the
        # container 503 forever on the declared Postgres path. Probe the
        # connection the store actually uses, through app.db, and say so.
        try:
            conn = db_connect()
            try:
                conn.execute("SELECT 1")
            finally:
                conn.close()
            db_ok = True
            db_detail = "postgres (DATABASE_URL)"
        except Exception as exc:  # noqa: BLE001
            db_detail = f"postgres: {type(exc).__name__}"
    elif not disk_ok or db_path is None:
        db_detail = "persistent disk missing"
    elif not db_path.exists():
        db_detail = "platform.db missing"
    else:
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("SELECT 1")
            finally:
                conn.close()
            db_ok = True
            db_detail = str(db_path)
        except sqlite3.Error as exc:
            db_detail = type(exc).__name__
    checks.append({"name": "database", "ok": db_ok, "detail": db_detail})
    if postgres and not disk_ok:
        # A Postgres deployment still needs its artifact directory, but the
        # database check above no longer depends on the sqlite filename; the
        # disk check already reports the missing path under its own name.
        pass

    mig_ok = False
    mig_detail = "not checked"
    if not db_ok:
        mig_detail = "database missing"
    else:
        try:
            from app.migrations import current_revision, head_revision

            current = current_revision()
            head = head_revision()
            mig_ok = bool(current) and current == head
            mig_detail = f"current={current} head={head}"
        except Exception as exc:  # noqa: BLE001 â€” health must not raise
            mig_detail = type(exc).__name__
    checks.append({"name": "migrations", "ok": mig_ok, "detail": mig_detail})

    ok = all(bool(item["ok"]) for item in checks)
    body = {
        "ok": ok,
        "status": "ok" if ok else "not_ready",
        "checks": checks,
        "revision": current_app_revision(),
        "mark": current_app_mark(),
    }
    return (200 if ok else 503, body)


def health_response() -> JSONResponse:
    code, body = evaluate_health()
    return JSONResponse(status_code=code, content=body)
