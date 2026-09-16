"""Handler for capability record_check_in.

Written by the factory WRITER role (codewhale exec)

Records one guest check-in at the front desk: the row the clerk typed is
validated by the vendored ``validation`` pipeline and written to the
platform database through the vendored ``database`` block, then persisted to
this capability's own alembic entity so the front desk can read it back.

Scope
-----
READS  the caller's record (this capability's own columns); app.dispatch (the
       local offline block runtime); app.block_inputs (constructed block
       inputs); app.store (the ``record_check_in`` table).
WRITES app.dispatch.execute() results; exactly ONE row in ``record_check_in``
       through ``store.save(ENTITY, record)``.
NEVER  network / HTTP store callbacks; ``vendor/**`` (sealed); another
       capability's table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword, never a payload key.
Every block input is constructed here -- the caller is never asked for
``table``, ``values`` or any other block-contract key.

Authored by the WRITER coding agent -- the factory's coder CLI, codewhale exec.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.dispatch import execute

CAPABILITY_ID = "record_check_in"
ENTITY = "record_check_in"
BLOCK_IDS = ["database", "validation"]
#: Each block's declared action for this capability. ``database`` accepts
#: query|insert|update|delete|create_table|list_tables (a check-in is an
#: insert); ``validation`` declares validate_pipeline.
BLOCK_DEFAULT_ACTIONS = {"database": "insert", "validation": "validate_pipeline"}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the names must be declared here as domain data.
CAPABILITY_FIELDS = [
    "reference",
    "guest_name",
    "room_number",
    "checked_in_at",
    "guests_count",
    "status",
    "notes",
]

#: The envelope vocabulary, enforced at the handler edge too, so a direct
#: handle() call cannot store a status the schema forbids.
STATUS_VALUES = ("open", "in_progress", "closed")
REQUIRED_FIELDS = ("reference", "guest_name", "room_number", "status")

#: The validation pipeline validates dict-shaped items and needs a stable
#: identity for the row it is judging.
VALIDATION_ITEM_TYPE = "guest_check_in"
_FAILURE_STATUSES = frozenset({"error", "failed", "failure", "partial", "timeout"})
_VALIDATION_FAIL_STATUSES = frozenset({"fail", "failed", "error"})


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
    """Shape a constructed block input into what the block actually accepts.

    ``prepare_block_input`` fills only keys that are missing, so every value
    built here survives; ``split_execute_action`` lifts ``action`` out of the
    payload so the operation travels as the keyword only.
    """
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


def _validation_inputs(record: Dict[str, Any]) -> Dict[str, Any]:
    """The item the vendored validation pipeline judges, built from the record.

    ``id`` and ``type`` are the pipeline's own shape requirement -- they are
    constructed here, never demanded from the caller.
    """
    item: Dict[str, Any] = dict(record)
    item["id"] = str(record.get("reference") or "check-in")
    item["type"] = VALIDATION_ITEM_TYPE
    return {
        "item": item,
        "context": {
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "room_number": record.get("room_number"),
            "checked_in_at": record.get("checked_in_at"),
        },
    }


def _validation_refused(result: Dict[str, Any]) -> str:
    """The first failing pipeline stage, or '' when the pipeline accepted."""
    if str(result.get("status") or "").lower() not in _VALIDATION_FAIL_STATUSES:
        return ""
    for stage in result.get("stages") or []:
        if not isinstance(stage, dict):
            continue
        if str(stage.get("status") or "").lower() in _VALIDATION_FAIL_STATUSES:
            issues = stage.get("issues") or []
            return "%s: %s" % (stage.get("stage"), "; ".join(str(i) for i in issues)[:160])
    return "validation pipeline refused the record"


def _database_inputs(record: Dict[str, Any]) -> Dict[str, Any]:
    """The insert the vendored database block runs. Table and values only."""
    values = {
        key: value
        for key, value in record.items()
        if isinstance(value, (str, int, float, bool))
    }
    return {"table": ENTITY, "values": values}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record one guest check-in, run its blocks, then persist one row."""
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

    plan: "Tuple[Tuple[str, Dict[str, Any]], ...]" = (
        ("database", _database_inputs(record)),
        ("validation", _validation_inputs(record)),
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

    validation = results.get("validation")
    if not errors and isinstance(validation, dict):
        refused = _validation_refused(validation)
        if refused:
            errors["validation"] = refused

    if errors:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
            "results": results,
        }

    stored = _persist_record(record)
    inserted = results.get("database") or {}
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "entity": ENTITY,
        "check_in": {
            "reference": record.get("reference"),
            "guest_name": record.get("guest_name"),
            "room_number": record.get("room_number"),
            "checked_in_at": record.get("checked_in_at"),
            "guests_count": record.get("guests_count"),
            "status": record.get("status"),
        },
        "database": {
            "inserted": inserted.get("inserted"),
            "rows_affected": inserted.get("rows_affected"),
        },
        "validation": {
            "status": (validation or {}).get("status") if isinstance(validation, dict) else None,
            "stages": len((validation or {}).get("stages") or []) if isinstance(validation, dict) else 0,
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
