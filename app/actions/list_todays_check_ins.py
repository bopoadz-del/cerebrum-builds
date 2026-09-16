"""Handler for capability list_todays_check_ins.

Written by the factory WRITER role (codewhale exec)

Displays the check-ins recorded for the current day. The day's rows are read
from the platform database through the vendored ``database`` block, rendered
as a front-desk list by the vendored ``dashboard`` block, and the day's
snapshot is persisted to this capability's own alembic entity so the desk can
read the list back.

Scope
-----
READS  the caller's own columns (the reference day and desk position);
       app.dispatch (the local offline block runtime); app.block_inputs;
       app.store (the ``list_todays_check_ins`` table).
WRITES app.dispatch.execute() results; exactly ONE row in
       ``list_todays_check_ins`` through ``store.save(ENTITY, record)``.
NEVER  network / HTTP store callbacks; ``vendor/**`` (sealed); another
       capability's table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword, never a payload key.
The SQL, the table name and the dashboard widget are constructed here -- the
caller is never asked for a block-contract key.

Authored by the WRITER coding agent -- the factory's coder CLI, codewhale exec.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.dispatch import execute

CAPABILITY_ID = "list_todays_check_ins"
ENTITY = "list_todays_check_ins"
BLOCK_IDS = ["database", "dashboard"]
#: Each block's declared default action (vendor/blocks/<id>/block.json):
#: database -> query, dashboard -> render.
BLOCK_DEFAULT_ACTIONS = {"database": "query", "dashboard": "render"}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    "reference",
    "check_in_date",
    "room_number",
    "guest_name",
    "check_in_count",
    "status",
    "notes",
]

STATUS_VALUES = ("open", "in_progress", "closed")
REQUIRED_FIELDS = ("reference", "check_in_date", "room_number", "guest_name", "status")

#: The check-in rows the desk is listing. This capability reads the check-in
#: table written by ``record_check_in`` and filters it to the requested day.
SOURCE_TABLE = "record_check_in"
SOURCE_DATE_FIELD = "checked_in_at"
_FAILURE_STATUSES = frozenset({"error", "failed", "failure", "partial", "timeout"})


def _persist_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Factory-grounded one-record persist. PRODUCT re-reads this entity.

    ``store`` is imported here, not at module load: an isolated contract probe
    execs this file against the factory ``app`` package, which has no product
    ``app.store``. A generated workspace always has one.
    """
    record = {k: v for k, v in (payload or {}).items() if k in CAPABILITY_FIELDS}
    try:
        from app import store as _store
    except ImportError:  # pragma: no cover - isolated contract probe
        return record
    return _store.save(ENTITY, record)


def _prepare(block_id: str, block_input: Dict[str, Any], action: str) -> Dict[str, Any]:
    """Shape a constructed block input into what the block actually accepts."""
    from app.block_inputs import prepare_block_input, split_execute_action

    resolved, data = split_execute_action(
        block_input, action=action, default_action=action
    )
    return prepare_block_input(
        block_id,
        data,
        action=resolved,
        roster=BLOCK_IDS,
        entity=ENTITY,
        default_actions=BLOCK_DEFAULT_ACTIONS,
    )


def _is_failure(result: Any) -> bool:
    """Did this block call fail? ``ok is False``/``error``/error statuses are."""
    if not isinstance(result, dict):
        return False
    if result.get("ok") is False or "error" in result:
        return True
    if str(result.get("status") or "").lower() in _FAILURE_STATUSES:
        return True
    steps = result.get("results")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and str(step.get("status") or "").lower() in _FAILURE_STATUSES:
                return True
    return False


def _database_inputs(record: Dict[str, Any]) -> Dict[str, Any]:
    """Read the check-in table with the vendored database block.

    The whole table is read and the day is selected here: the block's SQL
    surface is a plain SELECT over a table this platform owns, and the day
    filter is domain logic that belongs to the capability. Table and SQL are
    constructed, never demanded from the caller.
    """
    return {
        "table": SOURCE_TABLE,
        "sql": "SELECT * FROM " + SOURCE_TABLE,
        "params": [],
    }


def _day_rows(rows: Any, day: str) -> List[Dict[str, Any]]:
    """Rows whose recorded check-in falls on ``day`` (ISO date prefix)."""
    if not isinstance(rows, list):
        return []
    wanted = str(day or "").strip()
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        stamp = str(row.get(SOURCE_DATE_FIELD) or "")
        if not wanted or stamp.startswith(wanted):
            out.append(row)
    return out


def _dashboard_inputs(record: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The front-desk list the vendored dashboard block renders.

    Channel/transport keys are never asked of the caller: the widget, its
    data source and the desk position are constructed from the record.
    """
    day = record.get("check_in_date")
    columns = ["room_number", "guest_name", SOURCE_DATE_FIELD]
    return {
        "user_id": str(record.get("room_number") or "front_desk"),
        "title": "Check-ins for %s" % day,
        "type": "table",
        "data_source": "database",
        "widgets": [
            {
                "id": "todays_check_ins",
                "type": "table",
                "title": "Check-ins for %s" % day,
                "data_source": "database",
                "columns": columns,
                "limit": max(len(rows), 1),
            }
        ],
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """List the day's check-ins, run its blocks, then persist the snapshot."""
    if not isinstance(payload, dict):
        return {"ok": False, "capability": CAPABILITY_ID, "error": "payload must be an object"}

    record = {k: v for k, v in payload.items() if k in CAPABILITY_FIELDS}
    missing = [name for name in REQUIRED_FIELDS if record.get(name) in (None, "")]
    if missing:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "Missing required field: " + ", ".join(missing),
        }
    if record.get("status") not in STATUS_VALUES:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "status must be one of: " + ", ".join(STATUS_VALUES),
        }

    day = str(record.get("check_in_date") or "")
    plan: "Tuple[Tuple[str, Dict[str, Any]], ...]" = (
        ("database", _database_inputs(record)),
        ("dashboard", _dashboard_inputs(record, [])),
    )

    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id, block_input in plan:
        action = BLOCK_DEFAULT_ACTIONS.get(block_id)
        prepared = _prepare(block_id, block_input, action)
        try:
            outcome = execute(block_id, prepared, action=action)
        except Exception as exc:  # a block that cannot load is a refusal too
            outcome = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        results[block_id] = outcome
        if _is_failure(outcome):
            errors[block_id] = str(outcome.get("error") or outcome.get("status"))[:200]

    if errors:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
            "results": results,
        }

    database = results.get("database") or {}
    rows = _day_rows(database.get("rows"), day)
    stored = _persist_record({**record, "check_in_count": len(rows)})
    dashboard = results.get("dashboard") or {}

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "entity": ENTITY,
        "day": day,
        "items": rows,
        "total": len(rows),
        "rendered": {
            "title": dashboard.get("layout", {}).get("name") if isinstance(dashboard.get("layout"), dict) else None,
            "widgets": len(dashboard.get("widgets") or []) if isinstance(dashboard, dict) else 0,
            "theme": dashboard.get("theme") if isinstance(dashboard, dict) else None,
        },
        "stored": stored,
        "results": results,
    }


__all__ = [
    "BLOCK_DEFAULT_ACTIONS",
    "BLOCK_IDS",
    "CAPABILITY_FIELDS",
    "CAPABILITY_ID",
    "ENTITY",
    "handle",
]
