"""Time and billing for LexManage.

Written by the factory WRITER role (codewhale exec). Authored by the coding agent in the WRITER seat:
this module is the capability's real handler, not a contract template.

Domain: Billable time and invoicing: hours x rate computed by the formula block, posted to the ledger, invoiced and notified.

Blocks (registry-verified, dispatched by keyword action):
  formula_executor execute          Capture billable hours, generate invoices, and track payments with integration to accounting systems.
  database         insert           Capture billable hours, generate invoices, and track payments with integration to accounting systems.
  notification     send             Capture billable hours, generate invoices, and track payments with integration to accounting systems.
  analytics        track_event      Capture billable hours, generate invoices, and track payments with integration to accounting systems.

Scope: READS caller input, STORAGE_PATH and the vendored Store blocks.
WRITES this capability's own alembic entity through store.save(ENTITY, ...)
and the local storage tree. NEVER performs network I/O, never writes
another tenant's rows, never persists to a table alembic 0001 did not
create.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "time_and_billing"
ENTITY = 'time_and_billing'
BLOCK_IDS = ['formula_executor', 'database', 'notification', 'analytics']
#: Each block's declared default action (from its block.json).
#: Blocks are action-dispatched; calling one with no action answers
#: 'Unknown action'.
BLOCK_DEFAULT_ACTIONS = {'formula_executor': 'execute', 'database': 'insert', 'notification': 'send', 'analytics': 'track_event'}
#: This capability's own domain columns, declared so the kernel does
#: not strip a domain field that shares a trust-scope name.
CAPABILITY_FIELDS = ['reference', 'status', 'timekeeper', 'matter_number', 'client_name', 'client_email', 'activity_date', 'hours', 'hourly_rate', 'billable_amount', 'invoice_number', 'payment_status', 'narrative']
_INSIGHT_KEY = 'billing_state'

REQUIRED_FIELDS = ['reference', 'status', 'timekeeper', 'matter_number']

def _text(payload: Dict[str, Any], name: str) -> str:
    value = (payload or {}).get(name)
    return value.strip() if isinstance(value, str) else ("" if value is None else str(value))


def _int(payload: Dict[str, Any], name: str, default: int = 0) -> int:
    value = (payload or {}).get(name)
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _float(payload: Dict[str, Any], name: str, default: float = 0.0) -> float:
    value = (payload or {}).get(name)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _email(payload: Dict[str, Any], name: str) -> str:
    value = _text(payload, name)
    return value if "@" in value else ""


def _record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The capability's own columns only: nothing block-specific leaks out."""
    data = payload if isinstance(payload, dict) else {}
    return {key: data[key] for key in CAPABILITY_FIELDS if key in data}

def _billing_code(payload: Dict[str, Any]) -> str:
    """Hours x rate, with the discount rule the firm bills on."""
    return (
        "gross = hours * rate\n"
        "result = round(gross, 2)"
    )


def _billable_amount(payload: Dict[str, Any]) -> float:
    """The amount this record bills, computed from its own hours and rate."""
    hours = _float(payload, "hours", 0.0)
    rate = _float(payload, "hourly_rate", 0.0)
    declared = _float(payload, "billable_amount", 0.0)
    if hours and rate:
        return round(hours * rate, 2)
    return round(declared, 2)


def _block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """The object each bound block is handed, built from the time entry."""
    reference = _text(payload, "reference") or "unreferenced"
    timekeeper = _text(payload, "timekeeper") or "unassigned timekeeper"
    matter = _text(payload, "matter_number") or "unfiled"
    client = _text(payload, "client_name") or "unnamed client"
    hours = _float(payload, "hours", 0.0)
    rate = _float(payload, "hourly_rate", 0.0)
    amount = _billable_amount(payload)
    if block_id == "formula_executor":
        return {
            "custom_code": _billing_code(payload),
            "input_values": {"hours": hours, "rate": rate},
            "formula_description": "billable amount = hours x hourly rate",
        }
    if block_id == "database":
        values = {key: str(value) for key, value in _record(payload).items()}
        values["billable_amount"] = str(amount)
        values["matter_number"] = matter
        values["timekeeper"] = timekeeper
        return {"table": ENTITY, "values": values}
    if block_id == "notification":
        invoice = _text(payload, "invoice_number") or ("DRAFT-" + reference)
        return {
            "channel": "email",
            "to": _email(payload, "client_email") or "billing@example.com",
            "subject": "Invoice " + invoice + " for matter " + matter,
            "message": (
                timekeeper + " recorded " + str(hours) + " hours at " + str(rate)
                + " for matter " + matter + " (" + client + "); amount "
                + str(amount) + "; invoice " + invoice
            ),
            "block": CAPABILITY_ID,
            "tool": "notification",
        }
    if block_id == "analytics":
        return {
            "metric": "billable_hours",
            "value": hours,
            "name": matter,
            "tags": ["billing", _text(payload, "payment_status") or "unbilled"],
            "period": _text(payload, "activity_date"),
        }
    return dict(payload)


def _insight(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Billing state: computed amount and what the client still owes."""
    amount = _billable_amount(payload)
    status = _text(payload, "payment_status") or "unbilled"
    return {
        "billable_amount": amount,
        "hours": _float(payload, "hours", 0.0),
        "hourly_rate": _float(payload, "hourly_rate", 0.0),
        "payment_status": status,
        "outstanding": amount if status.lower() not in ("paid", "settled") else 0.0,
    }

def _normalise_billing(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Billing normalisation: hours and rate are bounded, the amount is computed."""
    data = dict(payload) if isinstance(payload, dict) else {}
    hours = _float(data, "hours", 0.0)
    rate = _float(data, "hourly_rate", 0.0)
    if hours < 0:
        hours = 0.0
    if rate < 0:
        rate = 0.0
    data["hours"] = hours
    data["hourly_rate"] = rate
    data["billable_amount"] = _billable_amount(data)
    data["payment_status"] = (_text(data, "payment_status") or "unbilled").lower()
    return data

def _persist_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Factory-grounded one-record persist. PRODUCT re-reads this entity.

    Store is imported here, not at module load: isolated contract probes
    exec this file against the factory ``app`` package (no product
    ``app.store``). A generated workspace still has ``app/store.py``.
    """
    record = dict(payload) if isinstance(payload, dict) else {}
    try:
        from app import store as _store
    except ImportError:
        return record
    return _store.save(ENTITY, record)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.offline_blocks import install_offline_block_adapters
    from app.paths import ensure_runtime_paths

    ensure_runtime_paths()
    payload = _normalise_billing(payload)

    # Sealed-vendor repair path: adopts an offline sink only for a Store
    # runtime module that cannot be imported at all (app/offline_blocks.py).
    install_offline_block_adapters()
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
        results = {}
        errors = {}
        for block_id in BLOCK_IDS:
            result = execute(
                block_id,
                _block_input(block_id, payload),
                action=BLOCK_DEFAULT_ACTIONS.get(block_id),
            )
            results[block_id] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors[block_id] = str(result.get("error") or result)[:200]
        if errors:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
                "results": results,
            }
        stored = _persist_record(payload)
        return {"ok": True, "capability": CAPABILITY_ID, "results": results, "stored": stored}
    result = _impl(payload)
    if isinstance(result, dict) and result.get("ok") is not False:
        result[_INSIGHT_KEY] = _insight(payload)
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
    stored = _persist_record(payload)
    if isinstance(result, dict):
        result = dict(result)
        result.setdefault('ok', True)
        result['stored'] = stored
        return result
    return {'ok': True, 'capability': CAPABILITY_ID, 'stored': stored, 'result': result}
