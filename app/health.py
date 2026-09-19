"""Fail-closed health surface.

Written by the factory WRITER role (codewhale exec)

``GET /health`` answers 200 only when the process can serve: the STORAGE_PATH
directory is really there and writable, the database answers a query *and* the
capability schema is present, Alembic is at head, and every bound block loads.
Anything else is 503 with the failing check named — a health route that says
"ok" while the migration is behind is how a broken deploy passes a probe.

Checks are reported as a list of ``{name, ok, detail}`` so an operator (and the
acceptance script) can see *which* boundary failed, and the body carries the
revision/mark the process is actually running as (``app.revision``).

Nothing here creates anything: the disk check probes for an existing directory
and a writable file, so a health call cannot turn a missing volume into a
present one.

Scope
-----
READS  ``STORAGE_PATH``, the database, the alembic head, ``vendor/blocks/**``
       (import only), ``APP_REVISION``/``APP_MARK``.
WRITES one short-lived probe file inside ``STORAGE_PATH`` (deleted in the same
       call).
NEVER  network, HTTP store callbacks, ``vendor/**`` writes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi.responses import JSONResponse

from app.revision import active_mark, active_revision

#: Checks whose failure means "this process is not ready", in report order.
REQUIRED_CHECKS = ("process", "persistent_disk", "database", "migrations")

#: The capability tables a ready database must have migrated.
REQUIRED_TABLES = (
    "stock_inventory_management",
    "product_pricing",
    "delivery_dispatch_tracking",
    "fleet_cost_tracking",
    "management_reporting_dashboard",
    "user_roles_workforce",
    "document_knowledge_qa",
    "procedures_readiness_and_audit_trail",
)


def _check(name: str, ok: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def _storage_root() -> Path:
    return Path(os.getenv("STORAGE_PATH", "./data")).expanduser()


def _process_check() -> Dict[str, Any]:
    import sys

    return _check("process", True, f"python {sys.version.split()[0]} pid {os.getpid()}")


def _disk_check() -> Dict[str, Any]:
    root = _storage_root()
    if not root.is_dir():
        return _check("persistent_disk", False, f"STORAGE_PATH {root} is not a directory")
    probe = root / ".health-write-probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return _check("persistent_disk", False, f"{root} is not writable: {exc}")
    return _check("persistent_disk", True, str(root))


def _database_check() -> Dict[str, Any]:
    from app import store

    try:
        conn = store.connect()
        try:
            conn.execute("SELECT 1").fetchone()
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 - a refusal is a health answer
        return _check("database", False, f"{type(exc).__name__}: {exc}")
    present = {row[0] for row in rows}
    missing = [name for name in REQUIRED_TABLES if name not in present]
    if missing:
        return _check(
            "database", False, "database answers but is not migrated: missing " + ", ".join(missing)
        )
    return _check("database", True, f"{len(present)} table(s) at {store.db_path()}")


def _migration_check() -> Dict[str, Any]:
    from app.migrations import current_revision, head_revision

    try:
        current = current_revision()
        head = head_revision()
    except Exception as exc:  # noqa: BLE001
        return _check("migrations", False, f"{type(exc).__name__}: {exc}")
    if not head:
        return _check("migrations", False, "no alembic head revision found in alembic/versions")
    if current != head:
        return _check("migrations", False, f"database is at {current!r}, head is {head!r}")
    return _check("migrations", True, f"at head {head}")


def _blocks_check() -> Dict[str, Any]:
    try:
        from app.dispatch import block_is_available
    except Exception as exc:  # noqa: BLE001
        return _check("blocks", False, f"{type(exc).__name__}: {exc}")
    from app.jobs import CAPABILITIES

    wanted: List[str] = []
    for item in CAPABILITIES:
        for block_id in item.get("blocks") or []:
            if block_id not in wanted:
                wanted.append(block_id)
    unavailable = [block_id for block_id in wanted if not block_is_available(block_id)]
    if unavailable:
        return _check("blocks", False, "unavailable bound block(s): " + ", ".join(unavailable))
    return _check("blocks", True, f"{len(wanted)} bound block(s) load in-process")


def checks() -> List[Dict[str, Any]]:
    """Every health check, performed in dependency order."""
    results = [_process_check()]
    disk = _disk_check()
    results.append(disk)
    if not disk["ok"]:
        results.append(_check("database", False, "skipped: persistent_disk is not ready"))
        results.append(_check("migrations", False, "skipped: persistent_disk is not ready"))
    else:
        results.append(_database_check())
        results.append(_migration_check())
    results.append(_blocks_check())
    return results


def evaluate_health() -> Tuple[int, Dict[str, Any]]:
    """``(status_code, body)``: 200 only when every check passed."""
    performed = checks()
    ok = all(bool(item["ok"]) for item in performed)
    failures = [item for item in performed if not item["ok"]]
    body: Dict[str, Any] = {
        "ok": ok,
        "status": "ok" if ok else "not_ready",
        "product": "bakery",
        "revision": active_revision(),
        "mark": active_mark(),
        "checks": performed,
    }
    if not ok:
        body["degraded"] = True
        body["summary"] = "degraded: " + "; ".join(
            f"{item['name']} ({item['detail']})" for item in failures
        )
    return (200 if ok else 503), body


def health_checks() -> Dict[str, Any]:
    """Back-compat mapping view of the checks (name -> {ok, detail})."""
    return {item["name"]: {"ok": item["ok"], "detail": item["detail"]} for item in checks()}


def health_response() -> JSONResponse:
    code, body = evaluate_health()
    return JSONResponse(status_code=code, content=body)
