"""Fail-closed health for Render and the local drill.

A 200 means this process is serving, STORAGE_PATH is a writable persistent
disk, the configured database answers one round trip, and Alembic is at head.
Anything else is 503. An unconditional ok:true is the LotDesk class of defect
and is forbidden here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi.responses import JSONResponse

from app.revision import current_app_mark, current_app_revision


def _storage_root() -> Path | None:
    raw = os.getenv("STORAGE_PATH")
    if not raw:
        return None
    return Path(raw)


def evaluate_health() -> Tuple[int, Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    checks.append({"name": "process", "ok": True, "detail": f"pid={os.getpid()}"})

    storage = _storage_root()
    if storage is None:
        disk_ok, disk_detail = False, "STORAGE_PATH unset"
    elif not storage.exists():
        disk_ok, disk_detail = False, f"missing {storage}"
    elif not os.access(storage, os.R_OK | os.W_OK):
        disk_ok, disk_detail = False, f"not writable {storage}"
    else:
        disk_ok, disk_detail = True, str(storage)
    checks.append({"name": "persistent_disk", "ok": disk_ok, "detail": disk_detail})

    db_ok = False
    db_detail = "not checked"
    from app.db import backend_name, is_postgres

    if not disk_ok and not is_postgres():
        db_detail = "persistent disk missing"
    else:
        try:
            from app.store import health as store_health

            probe = store_health()
            db_ok = bool(probe.get("ok"))
            db_detail = f"{probe.get('backend') or backend_name()}"
        except Exception as exc:  # noqa: BLE001 -- health must never raise
            db_detail = f"{type(exc).__name__}: {exc}"[:160]
    checks.append({"name": "database", "ok": db_ok, "detail": db_detail})

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
        except Exception as exc:  # noqa: BLE001 -- health must not raise
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
