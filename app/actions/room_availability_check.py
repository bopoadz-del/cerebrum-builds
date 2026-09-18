"""Handler for capability room_availability_check.

Written by the factory WRITER role (codewhale exec)

Answers whether a room is free for the requested dates. The vendored
``formula_executor`` slice computes the stay length and the room
charge, the vendored ``database`` slice reads the booking surface so
overlapping stays are visible, and the vendored ``validation`` slice
confirms the blocks this capability declares are available.

Scope
-----
READS  the caller's own record (reference, room_number, check_in_date, check_out_date, is_available, status); app.dispatch (the local offline
       block runtime); app.block_inputs (constructed block inputs).
WRITES app.dispatch.execute() results only. Persistence is route-scoped: the
       ROUTE writes the request through the tenant-scoped store after SUCCESS,
       so handle() has no tenant and must not write a row itself
       (Phase 2 section 0.2).
NEVER  network / HTTP store callbacks; ``vendor/**`` (sealed, read-only);
       another capability's entity; ``tests/**``.

Blocks are action-dispatched: ``action=`` travels as a keyword, never inside
the payload. Every block input is constructed here -- the caller is never
asked for ``sql``, ``topic``, ``payload`` or any other block-contract key.

``validation``        confirms the declared block roster is available
(validate_dependencies);
``database``          reads the booking surface (query);
``formula_executor``  computes nights and charge (execute).

Blocks: validation=validate_dependencies, database=query, formula_executor=execute

Authored by the WRITER coding agent -- the factory's coder CLI, codewhale exec.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "room_availability_check"
ENTITY = 'room_availability_check'
BLOCK_IDS = ['validation', 'database', 'formula_executor']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {
    'validation': 'validate_dependencies',
    'database': 'query',
    'formula_executor': 'execute',
}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'room_number', 'check_in_date', 'check_out_date', 'is_available', 'status']


#: Envelope vocabulary, enforced at the handler edge as well as the schema, so
#: a direct handle() call cannot store a status the contract forbids.
STATUS_VALUES = ("open", "in_progress", "closed")
REQUIRED_FIELDS = ('reference', 'room_number', 'check_in_date', 'check_out_date', 'status')
#: A block answer that says the call did not work.
_FAILED_STATUSES = frozenset({"error", "failed", "failure", "partial", "timeout"})


def _failed(outcome):
    """The refusal text of a block answer, or None when the block accepted."""
    if not isinstance(outcome, dict):
        return None
    status = str(outcome.get("status") or "").lower()
    if status in _FAILED_STATUSES or outcome.get("ok") is False:
        return str(outcome.get("error") or outcome.get("status"))[:200]
    return None


def _summary(record, label):
    """One-line human record summary handed to the blocks that take text."""
    parts = [f"{k}={v}" for k, v in sorted(record.items()) if v not in (None, "")]
    return (label + ": " + "; ".join(parts))[:500]


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CONSTANTS = {"nightly_rate": 145.0, "max_stay_nights": 30, "currency": "USD"}
_CHARGE_CODE = "result = nights * nightly_rate\n"


def _nights(record):
    """Stay length in nights, or None when the dates are unusable.

    A same-day range is a legal zero-night turnover; only a reversed range is
    refused, so the capability accepts the payload its own schema samples.
    """
    try:
        start = date.fromisoformat(str(record.get("check_in_date") or ""))
        end = date.fromisoformat(str(record.get("check_out_date") or ""))
    except ValueError:
        return None
    delta = (end - start).days
    return delta if delta >= 0 else None


def _overlaps(row, room, start, end):
    """Does a recorded booking for this room overlap [start, end)?"""
    if str(row.get("room_number") or "") != room:
        return False
    try:
        other_in = date.fromisoformat(str(row.get("check_in_date") or ""))
        other_out = date.fromisoformat(str(row.get("check_out_date") or ""))
    except ValueError:
        return False
    return other_in < end and start < other_out


def _block_input(block_id, record):
    if block_id == "validation":
        return {"block_id": CAPABILITY_ID, "dependencies": list(BLOCK_IDS)}
    if block_id == "database":
        return {"table": ENTITY, "sql": f"SELECT * FROM {ENTITY}"}
    if block_id == "formula_executor":
        nights = _nights(record) or 0
        return {
            "formula_description": "room charge for a stay",
            "input_values": {"nights": nights, "nightly_rate": CONSTANTS["nightly_rate"]},
            "custom_code": _CHARGE_CODE,
        }
    return dict(record)


def _guard(record):
    problems = [n for n in REQUIRED_FIELDS if record.get(n) in (None, "")]
    if problems:
        return "Missing required field: " + ", ".join(problems)
    if str(record.get("status")) not in STATUS_VALUES:
        return "status must be one of: " + ", ".join(STATUS_VALUES)
    if not DATE_RE.match(str(record.get("check_in_date") or "")):
        return "check_in_date must be YYYY-MM-DD"
    if not DATE_RE.match(str(record.get("check_out_date") or "")):
        return "check_out_date must be YYYY-MM-DD"
    nights = _nights(record)
    if nights is None:
        return "check_out_date must not be earlier than check_in_date"
    if nights > CONSTANTS["max_stay_nights"]:
        return f"stays longer than {CONSTANTS['max_stay_nights']} nights need a manager override"
    return None


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    import app.dispatch as _dispatch
    try:
        from app.block_inputs import prepare_block_input as _prepare_block_input
    except ImportError:  # pragma: no cover - unit stubs without the module
        def _prepare_block_input(block_id, data, **_kw):
            return data if isinstance(data, dict) else {'value': data}
    try:
        from app.block_inputs import default_block_action as _default_block_action
    except ImportError:  # pragma: no cover - unit stubs / older emit
        def _default_block_action(block_id, default_actions=None):
            defaults = default_actions if isinstance(default_actions, dict) else {}
            cand = defaults.get(block_id)
            return cand if isinstance(cand, str) and cand.strip() else None
    try:
        from app.block_inputs import split_execute_action as _split_execute_action
    except ImportError:  # pragma: no cover - unit stubs / older emit
        def _split_execute_action(payload, action=None, default_action=None):
            data = dict(payload) if isinstance(payload, dict) else (
                {} if payload is None else {'value': payload}
            )
            inner = data.get('input') if isinstance(data.get('input'), dict) else {}
            resolved = action
            if not (isinstance(resolved, str) and resolved.strip()):
                for cand in (data.get('action'), inner.get('action'), default_action):
                    if isinstance(cand, str) and cand.strip():
                        resolved = cand
                        break
                else:
                    resolved = default_action
            data.pop('action', None)
            if isinstance(data.get('input'), dict):
                data['input'] = dict(data['input'])
                data['input'].pop('action', None)
            return resolved, data
    _block_errors = []
    def _watched(block_id, *a, **kw):
        data = a[0] if a else kw.get('payload', {})
        action = kw.get('action')
        if action is None and len(a) > 1:
            action = a[1]
        params = kw.get('params')
        if params is None and len(a) > 2:
            params = a[2]
        action, data = _split_execute_action(
            data,
            action=action,
            default_action=_default_block_action(
                block_id, BLOCK_DEFAULT_ACTIONS
            ),
        )
        prepared = _prepare_block_input(
            block_id, data, action=action, roster=BLOCK_IDS,
            entity=ENTITY,
            default_actions=BLOCK_DEFAULT_ACTIONS,
        )
        if isinstance(prepared, dict):
            prepared = dict(prepared)
            prepared.pop('action', None)
            if isinstance(prepared.get('input'), dict):
                prepared['input'] = dict(prepared['input'])
                prepared['input'].pop('action', None)
        res = _dispatch.execute(
            block_id, prepared, action=action, params=params
        )
        if isinstance(res, dict) and (
            res.get("status") == "error" or "error" in res
        ):
            _block_errors.append(
                "%s: %s" % (block_id, str(res.get("error") or res.get("status"))[:160])
            )
        return res
    def _impl(payload, execute=_watched):

        record = {k: v for k, v in (payload or {}).items() if k in CAPABILITY_FIELDS}
        problem = _guard(record)
        if problem:
            return {"ok": False, "capability": CAPABILITY_ID, "error": problem}

        results = {}
        errors = {}
        for block_id in BLOCK_IDS:
            outcome = execute(
                block_id,
                _block_input(block_id, record),
                action=BLOCK_DEFAULT_ACTIONS.get(block_id),
            )
            results[block_id] = outcome
            refusal = _failed(outcome)
            if refusal:
                errors[block_id] = refusal
        if errors:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
                "results": results,
            }

        room = str(record.get("room_number"))
        start = date.fromisoformat(str(record.get("check_in_date")))
        end = date.fromisoformat(str(record.get("check_out_date")))
        nights = (end - start).days

        database = results.get("database") if isinstance(results.get("database"), dict) else {}
        rows = database.get("rows") if isinstance(database.get("rows"), list) else []
        conflicts = [
            {
                "room_number": row.get("room_number"),
                "check_in_date": row.get("check_in_date"),
                "check_out_date": row.get("check_out_date"),
            }
            for row in rows
            if isinstance(row, dict) and _overlaps(row, room, start, end)
        ]

        formula = results.get("formula_executor") if isinstance(results.get("formula_executor"), dict) else {}
        validation = results.get("validation") if isinstance(results.get("validation"), dict) else {}
        charge = formula.get("execution_result")
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "availability": {
                "room_number": room,
                "check_in_date": record.get("check_in_date"),
                "check_out_date": record.get("check_out_date"),
                "nights": nights,
                "is_available": not conflicts,
                "conflicts": conflicts,
                "double_booking_prevented": bool(conflicts),
            },
            "stay": {
                "nights": nights,
                "nightly_rate": CONSTANTS["nightly_rate"],
                "estimated_charge": charge if isinstance(charge, (int, float)) else None,
                "currency": CONSTANTS["currency"],
            },
            "validation": {"valid": validation.get("valid"), "missing": validation.get("missing")},
            "results": results,
        }
    result = _impl(payload)
    if _block_errors and (
        not isinstance(result, dict) or result.get("ok") is not False
    ):
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "block failed: " + "; ".join(_block_errors),
            "result": result,
        }
    if isinstance(result, dict) and result.get('ok') is False:
        return result
    if isinstance(result, dict):
        result = dict(result)
        result.setdefault('ok', True)
        return result
    return {'ok': True, 'capability': CAPABILITY_ID, 'result': result}
