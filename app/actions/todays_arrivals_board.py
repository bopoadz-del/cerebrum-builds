"""Handler for capability todays_arrivals_board.

Written by the factory WRITER role (codewhale exec)

Shows today's arrivals to the duty manager: the vendored ``dashboard``
slice renders the board, the vendored ``analytics`` slice records the
arrival metric, and the vendored ``database`` slice reads the arrival
surface this capability persists so the board carries a real count.

Scope
-----
READS  the caller's own record (reference, arrival_date, guest_name, room_number, arrived, arrivals_count, status); app.dispatch (the local offline
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

``dashboard``  renders the arrivals board (render);
``analytics``  records the arrival metric (track_event);
``database``   reads the arrival surface back (query).

Blocks: dashboard=render, analytics=track_event, database=query

Authored by the WRITER coding agent -- the factory's coder CLI, codewhale exec.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "todays_arrivals_board"
ENTITY = 'todays_arrivals_board'
BLOCK_IDS = ['dashboard', 'database', 'analytics']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {
    'dashboard': 'render',
    'database': 'query',
    'analytics': 'track_event',
}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'arrival_date', 'guest_name', 'room_number', 'arrived', 'arrivals_count', 'status']


#: Envelope vocabulary, enforced at the handler edge as well as the schema, so
#: a direct handle() call cannot store a status the contract forbids.
STATUS_VALUES = ("open", "in_progress", "closed")
REQUIRED_FIELDS = ('reference', 'arrival_date', 'guest_name', 'room_number', 'status')
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
CONSTANTS = {"house_rooms": 40, "max_board_rows": 200}


def _arrived(value):
    """The schema samples arrive=False; the board reports what it was told."""
    return bool(value)


def _block_input(block_id, record):
    if block_id == "dashboard":
        return {
            "title": f"Arrivals board {record.get('arrival_date')}",
            "status": record.get("status"),
            "widgets": ["arrivals_today", "not_yet_arrived", "rooms_free"],
        }
    if block_id == "analytics":
        return {
            "metric": "todays_arrivals",
            "value": _metric_value(record),
            "arrival_date": record.get("arrival_date"),
        }
    if block_id == "database":
        return {"table": ENTITY, "sql": f"SELECT * FROM {ENTITY}"}
    return dict(record)


def _metric_value(record):
    count = record.get("arrivals_count")
    if isinstance(count, bool) or not isinstance(count, int):
        return 1.0
    return float(count)


def _guard(record):
    problems = [n for n in REQUIRED_FIELDS if record.get(n) in (None, "")]
    if problems:
        return "Missing required field: " + ", ".join(problems)
    if not DATE_RE.match(str(record.get("arrival_date") or "")):
        return "arrival_date must be YYYY-MM-DD"
    if str(record.get("status")) not in STATUS_VALUES:
        return "status must be one of: " + ", ".join(STATUS_VALUES)
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

        database = results.get("database") if isinstance(results.get("database"), dict) else {}
        rows = database.get("rows") if isinstance(database.get("rows"), list) else []
        dashboard = results.get("dashboard") if isinstance(results.get("dashboard"), dict) else {}
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "board": {
                "arrival_date": record.get("arrival_date"),
                "guest_name": record.get("guest_name"),
                "room_number": record.get("room_number"),
                "arrived": _arrived(record.get("arrived")),
                "status": "arrived" if _arrived(record.get("arrived")) else "expected",
                "arrivals_count": record.get("arrivals_count"),
                "house_rooms": CONSTANTS["house_rooms"],
            },
            "dashboard": {
                "widgets": dashboard.get("widgets"),
                "layout": (dashboard.get("layout") or {}).get("name")
                if isinstance(dashboard.get("layout"), dict)
                else None,
            },
            "surface": (rows[0] if rows else {}),
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
