"""Fail-closed health: process, disk, database, migrations."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.migrations import current_revision, head_revision
from app.revision import current_mark, current_revision_label
from app.store import db_path

Check = Dict[str, Any]


def _check(name: str, ok: bool, detail: str = "") -> Check:
    return {"name": name, "ok": ok, "detail": detail}


def evaluate_health() -> Tuple[int, Dict[str, Any]]:
    checks: List[Check] = [_check("process", True, "app importable")]

    raw = os.environ.get("STORAGE_PATH") or "./data"
    root = Path(raw).resolve()
    disk_ok = root.is_dir() and os.access(root, os.W_OK)
    checks.append(
        _check(
            "persistent_disk",
            disk_ok,
            "writable directory" if disk_ok else f"missing or not writable: {root}",
        )
    )

    db_ok = False
    mig_ok = False
    if disk_ok:
        path = db_path()
        if path.is_file():
            try:
                conn = sqlite3.connect(str(path))
                try:
                    conn.execute("SELECT 1")
                    tables = {
                        row[0]
                        for row in conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )
                    }
                    db_ok = "productivity_core" in tables and "audit" in tables
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                db_ok = False
                checks.append(_check("database", False, str(exc)))
        if db_ok:
            checks.append(_check("database", True, str(path)))
        elif not any(item["name"] == "database" for item in checks):
            checks.append(_check("database", False, "platform.db missing or unmigrated"))

        rev = current_revision()
        head = head_revision()
        mig_ok = bool(rev) and rev == head
        checks.append(
            _check(
                "migrations",
                mig_ok,
                f"revision={rev} head={head}",
            )
        )
    else:
        checks.append(_check("database", False, "disk not ready"))
        checks.append(_check("migrations", False, "disk not ready"))

    ok = all(item["ok"] for item in checks)
    body = {
        "ok": ok,
        "status": "ok" if ok else "not_ready",
        "checks": checks,
        "revision": current_revision_label(),
        "mark": current_mark(),
        "storage": str(root),
        "db": str(db_path()),
    }
    return (200 if ok else 503), body
