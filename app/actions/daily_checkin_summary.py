"""Handler for capability daily_checkin_summary.

Written by the factory WRITER role (codewhale exec)

Produces the end-of-day arrivals summary for the manager. The
vendored ``analytics`` slice records the day's arrival metric, the
vendored ``database`` slice reads the summary surface back, and the
vendored ``dashboard`` slice renders the manager's summary card.

Scope
-----
READS  the caller's own record (reference, summary_date, arrivals_count, occupancy_percent, no_show_count, status); app.dispatch (the local offline
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

``analytics``  records the day's arrival metric (track_event);
``database``   reads the summary surface (query);
``dashboard``  renders the summary card (render).

Blocks: analytics=track_event, database=query, dashboard=render

Authored by the WRITER coding agent -- the factory's coder CLI, codewhale exec.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "daily_checkin_summary"
ENTITY = 'daily_checkin_summary'
BLOCK_IDS = ['analytics', 'database', 'dashboard']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {
    'analytics': 'track_event',
    'database': 'query',
    'dashboard': 'render',
}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'summary_date', 'arrivals_count', 'occupancy_percent', 'no_show_count', 'status']


#: Envelope vocabulary, enforced at the handler edge as well as the schema, so
#: a direct handle() call cannot store a status the contract forbids.
STATUS_VALUES = ("open", "in_progress", "closed")
REQUIRED_FIELDS = ('reference', 'summary_date', 'status')
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
CONSTANTS = {"house_rooms": 40, "max_arrivals": 500}


def _metric_value(record):
    arrivals = record.get("arrivals_count")
    if isinstance(arrivals, bool) or not isinstance(arrivals, int):
        return 1.0
    return float(arrivals)


def _no_shows(record):
    value = record.get("no_show_count")
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _coerce_occupancy(value):
    """The caller's occupancy as a float, or None when it was not supplied.

    ``occupancy_percent`` is declared optional and numeric on the spec
    (app/models.py: float, min 0, max 100). A payload the spec's own sample
    builder emits can still carry a placeholder string; the field is
    optional, so an unparseable placeholder means "not supplied" and the
    handler computes occupancy from ``arrivals_count`` below -- the same
    path an omitted field takes. Real numbers are never guessed: they are
    range-checked in :func:`_guard` and refused when impossible.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _occupancy(record):
    """Occupancy from the manager's own numbers; a 40-room house is the basis."""
    return _coerce_occupancy(record.get("occupancy_percent"))


def _block_input(block_id, record):
    if block_id == "analytics":
        return {
            "metric": "daily_checkin_summary",
            "value": _metric_value(record),
            "summary_date": record.get("summary_date"),
        }
    if block_id == "database":
        return {"table": ENTITY, "sql": f"SELECT * FROM {ENTITY}"}
    if block_id == "dashboard":
        return {
            "title": f"Daily check-in summary {record.get('summary_date')}",
            "status": record.get("status"),
            "widgets": ["arrivals", "occupancy", "no_shows"],
        }
    return dict(record)


def _guard(record):
    problems = [n for n in REQUIRED_FIELDS if record.get(n) in (None, "")]
    if problems:
        return "Missing required field: " + ", ".join(problems)
    if str(record.get("status")) not in STATUS_VALUES:
        return "status must be one of: " + ", ".join(STATUS_VALUES)
    if not DATE_RE.match(str(record.get("summary_date") or "")):
        return "summary_date must be YYYY-MM-DD"
    arrivals = record.get("arrivals_count")
    if isinstance(arrivals, bool) or (arrivals is not None and not isinstance(arrivals, int)):
        return "arrivals_count must be an integer"
    if isinstance(arrivals, int) and arrivals > CONSTANTS["max_arrivals"]:
        return f"arrivals_count exceeds {CONSTANTS['max_arrivals']}"
    occupancy = _coerce_occupancy(record.get("occupancy_percent"))
    if occupancy is not None and not 0 <= occupancy <= 100:
        return "occupancy_percent must be between 0 and 100"
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
        arrivals = record.get("arrivals_count")
        arrivals = arrivals if isinstance(arrivals, int) and not isinstance(arrivals, bool) else 0
        occupancy = _occupancy(record)
        if occupancy is None:
            occupancy = round(100.0 * min(arrivals, CONSTANTS["house_rooms"]) / CONSTANTS["house_rooms"], 2)
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "summary": {
                "summary_date": record.get("summary_date"),
                "arrivals_count": arrivals,
                "occupancy_percent": occupancy,
                "no_show_count": _no_shows(record),
                "house_rooms": CONSTANTS["house_rooms"],
                "status": record.get("status"),
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
