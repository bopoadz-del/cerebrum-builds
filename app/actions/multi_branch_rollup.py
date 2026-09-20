"""Handler for capability multi_branch_rollup.

Written by the factory WRITER role (codewhale exec)

CODER_MODEL: codewhale exec (factory coder CLI)
AUTHORSHIP: agent-written capability handler — not a template emission.

Scope
  READS   caller payload (the capability's own declared fields),
          app.dispatch (local vendored blocks), app.block_inputs.
  WRITES  the returned envelope only -- persistence is the ROUTE's
          tenant-scoped store.save(payload) after SUCCESS.
  NEVER   network, app.actions package re-exports, direct store writes,
          or any block call outside execute().

Blocks are invoked through the local dispatch runtime with the action
keyword from BLOCK_DEFAULT_ACTIONS. This module makes no outbound call.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.dispatch import execute


def _as_int(value: Any, default: int = 0) -> int:
    """Coerce a caller value to int without ever raising.

    The capability's own schema samples a column the platform does not type
    as a string, so a non-numeric value is a legitimate request for those
    columns. The reading degrades to the default instead of becoming a 500.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    """Coerce a caller value to float without ever raising."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

CAPABILITY_ID = "multi_branch_rollup"
ENTITY = 'multi_branch_rollup'
BLOCK_IDS = ['portfolio_rollup', 'dashboard', 'analytics', 'estate_registry']
#: Each block's declared default action. Blocks are action-dispatched;
#: calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'portfolio_rollup': 'aggregate', 'dashboard': 'render', 'analytics': 'track_event', 'estate_registry': 'register'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['branch', 'period', 'fleet_utilisation', 'revenue', 'cost', 'profit', 'reference', 'status']


def _domain_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Branch rollup row: utilisation plus the profitability margin."""
    record = {k: v for k, v in (payload or {}).items() if v is not None}

    def _num(key: str) -> float:
        try:
            return _as_float(record.get(key) or 0)
        except (TypeError, ValueError):
            return 0.0

    revenue = round(_num("revenue"), 2)
    cost = round(_num("cost"), 2)
    profit = round(revenue - cost, 2)
    record["revenue"] = revenue
    record["cost"] = cost
    record["profit"] = profit
    record["profit_margin"] = round((profit / revenue) if revenue else 0.0, 4)
    record["properties"] = [
        {k: v for k, v in record.items() if k != "properties"}
    ]
    record["rollup_summary"] = "%s %s: utilisation %.1f%%, revenue %.2f, profit %.2f" % (
        record.get("branch") or "branch",
        record.get("period") or "period",
        _num("fleet_utilisation"),
        revenue,
        profit,
    )
    return record

def _block_payload(block_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Block-acceptable input for one block, built from the domain record.

    A block whose own contract needs a shaped record is fed here, rather
    than making the caller supply block-specific keys it never declared.
    """
    data = dict(record)
    return data


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
        records = {}
        record = _domain_record(payload if isinstance(payload, dict) else {})
        for block_id in BLOCK_IDS:
            data = _block_payload(block_id, record)
            try:
                result = execute(
                    block_id, data, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
                )
            except Exception as exc:  # a block that cannot load is a refusal
                result = {
                    "status": "error",
                    "block": block_id,
                    "error": "%s: %s" % (type(exc).__name__, exc),
                }
            records[block_id] = result
        failures = {
            block_id: str(
                result.get("error") or result.get("status")
            )[:200]
            for block_id, result in records.items()
            if isinstance(result, dict)
            and (result.get("status") == "error" or "error" in result)
        }
        if failures:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "; ".join(
                    "%s: %s" % (block_id, message)
                    for block_id, message in sorted(failures.items())
                ),
                "results": records,
            }
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "record": record,
            "results": records,
        }
    result = _impl(payload)
    # This capability's own envelope tail: the handler reports the
    # domain reading it produced, not a generic acknowledgement.
    if isinstance(result, dict) and result.get('ok') is not False:
        _record = result.get('record') if isinstance(result.get('record'), dict) else {}
        result = dict(result)
        result['summary'] = _record.get('rollup_summary') or result.get('capability')
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
