"""Fail-closed health. Does not mkdir STORAGE_PATH."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.revision import current_mark, current_revision


def evaluate_health() -> Tuple[int, Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    checks.append({"name": "process", "ok": True, "detail": "process up"})

    raw = os.environ.get("STORAGE_PATH") or "./data"
    root = Path(raw)
    disk_ok = root.exists() and root.is_dir() and os.access(root, os.W_OK)
    checks.append(
        {
            "name": "persistent_disk",
            "ok": disk_ok,
            "detail": str(root) if disk_ok else f"STORAGE_PATH not writable: {root}",
        }
    )

    db_ok = False
    db_detail = "platform.db missing"
    db_file = root / "platform.db" if disk_ok else None
    if db_file is not None and db_file.is_file():
        try:
            conn = sqlite3.connect(str(db_file))
            try:
                conn.execute("SELECT 1")
            finally:
                conn.close()
            db_ok = True
            db_detail = str(db_file)
        except sqlite3.Error as exc:
            db_detail = str(exc)
    checks.append({"name": "database", "ok": db_ok, "detail": db_detail})

    mig_ok = False
    mig_detail = "migrations not at head"
    if db_ok:
        try:
            from app.migrations import current_revision as db_rev
            from app.migrations import head_revision

            now = db_rev()
            head = head_revision()
            mig_ok = now is not None and now == head
            mig_detail = f"{now} head={head}"
        except Exception as exc:
            mig_detail = str(exc)
    checks.append({"name": "migrations", "ok": mig_ok, "detail": mig_detail})

    ok = all(item["ok"] for item in checks)
    body = {
        "ok": ok,
        "status": "ok" if ok else "not_ready",
        "checks": checks,
        "revision": current_revision(),
        "mark": current_mark(),
    }
    return (200 if ok else 503), body
