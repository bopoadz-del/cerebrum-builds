"""Fail-closed health: process, persistent disk, database, migrations."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from app.migrations import HEAD, current_revision
from app.revision import current_app_mark, current_app_revision
from app.store import db_path, storage_path


def _disk_check() -> Dict[str, Any]:
    path = storage_path()
    ok = path.is_dir() and os.access(path, os.W_OK)
    return {"name": "persistent_disk", "ok": ok, "path": str(path)}


def _database_check(disk_ok: bool) -> Dict[str, Any]:
    path = db_path()
    ok = bool(disk_ok and path.is_file() and path.stat().st_size >= 0)
    if ok:
        try:
            import sqlite3

            conn = sqlite3.connect(str(path))
            try:
                conn.execute("SELECT 1")
            finally:
                conn.close()
        except Exception:
            ok = False
    return {"name": "database", "ok": ok, "path": str(path)}


def _migrations_check(db_ok: bool) -> Dict[str, Any]:
    revision = None
    ok = False
    if db_ok:
        try:
            revision = current_revision()
            ok = revision == HEAD
        except Exception:
            ok = False
    return {"name": "migrations", "ok": ok, "revision": revision}


def evaluate_health() -> Tuple[int, Dict[str, Any]]:
    checks: List[Dict[str, Any]] = [{"name": "process", "ok": True}]
    disk = _disk_check()
    checks.append(disk)
    database = _database_check(disk["ok"])
    checks.append(database)
    migrations = _migrations_check(database["ok"])
    checks.append(migrations)
    ok = all(item["ok"] for item in checks)
    body = {
        "ok": ok,
        "status": "ok" if ok else "not_ready",
        "checks": checks,
        "revision": current_app_revision(),
        "mark": current_app_mark(),
        "storage": str(storage_path()),
        "db": str(db_path()),
    }
    return (200 if ok else 503, body)
