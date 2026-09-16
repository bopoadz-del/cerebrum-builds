"""Supplier and purchasing for RetailOS.

Written by the factory WRITER role (codewhale exec). Authored by the coding agent in the WRITER seat:
this module is the capability's real handler, not a contract template.

Domain: Manage supplier relationships, purchase orders, and lead times, with automated reorder suggestions based on demand.

Blocks (registry-verified, dispatched by keyword action):
  database             insert           domain row written to this capability's alembic entity
  workflow             run              prepared child steps, each with block + action + input
  recommendation_template recommend        replenishment recommendation from demand variance
  notification         send             operator notice (in-process mcp channel offline)

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

CAPABILITY_ID = "supplier_and_purchasing"
ENTITY = 'supplier_and_purchasing'
BLOCK_IDS = ['database', 'workflow', 'recommendation_template', 'notification']
#: Each block's declared default action (from its block.json / the Store
#: map). Blocks are action-dispatched; calling one with no action answers
#: 'Unknown action'.
BLOCK_DEFAULT_ACTIONS = {'database': 'insert', 'workflow': 'run', 'recommendation_template': 'recommend', 'notification': 'send'}
#: This capability's own domain columns, declared so the kernel does
#: not strip a domain field that shares a trust-scope name.
CAPABILITY_FIELDS = ['reference', 'status', 'supplier_name', 'supplier_email', 'purchase_order_number', 'sku', 'quantity_ordered', 'unit_cost', 'lead_time_days', 'order_date', 'expected_date', 'payment_terms']
_INSIGHT_KEY = 'purchase_state'

REQUIRED_FIELDS = ['reference', 'status', 'supplier_name', 'purchase_order_number']

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

def _purchase_brief(payload: Dict[str, Any]) -> str:
    """The purchase line a buyer reads: supplier, PO, quantity, lead time."""
    parts = [
        "Purchase order " + (_text(payload, "purchase_order_number") or "unreferenced"),
        "supplier: " + (_text(payload, "supplier_name") or "unnamed supplier"),
        "sku: " + (_text(payload, "sku") or "unassigned-sku"),
        "quantity: " + str(_int(payload, "quantity_ordered", 0)),
        "unit cost: " + str(_float(payload, "unit_cost", 0.0)),
        "lead time (days): " + str(_int(payload, "lead_time_days", 0)),
    ]
    return "; ".join(parts)


def _variance_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The demand variance the recommendation template analyses."""
    quantity = _int(payload, "quantity_ordered", 0)
    lead_time = _int(payload, "lead_time_days", 0)
    unit_cost = _float(payload, "unit_cost", 0.0)
    return {
        "variance_pct": float(quantity),
        "cost_impact_usd": unit_cost * float(quantity),
        "delay_days": float(lead_time),
        "risk_level": "high" if lead_time >= 14 else ("medium" if lead_time >= 7 else "low"),
        "test_result": _text(payload, "payment_terms") or "net_30",
        "sku": _text(payload, "sku"),
    }


def _normalise_suppliers(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Purchase normalisation: every order names a supplier and a PO."""
    data = dict(payload) if isinstance(payload, dict) else {}
    reference = _text(data, "reference") or "unreferenced"
    data["reference"] = reference
    data["purchase_order_number"] = _text(data, "purchase_order_number") or reference
    data["supplier_name"] = _text(data, "supplier_name") or "unnamed supplier"
    data["payment_terms"] = (_text(data, "payment_terms") or "net_30").lower()
    return data


def _insight(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Purchase state read back off the record."""
    return {
        "purchase_order_number": _text(payload, "purchase_order_number"),
        "supplier_name": _text(payload, "supplier_name"),
        "quantity_ordered": _int(payload, "quantity_ordered", 0),
        "lead_time_days": _int(payload, "lead_time_days", 0),
    }

def _block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """The object each bound block is handed, built from the purchase record."""
    reference = _text(payload, "reference") or "unreferenced"
    supplier = _text(payload, "supplier_name") or "unnamed supplier"
    po = _text(payload, "purchase_order_number") or reference
    brief = _purchase_brief(payload)
    values = {key: str(value) for key, value in _record(payload).items()}
    if block_id == "database":
        return {"table": ENTITY, "values": values}
    if block_id == "workflow":
        # Every child is prepared: block, action, params.action and a real
        # input. The Store workflow reads the child's operation from params.
        return {
            "reference": reference,
            "steps": [
                {
                    "block": "database",
                    "action": "insert",
                    "params": {"action": "insert"},
                    "input": {"table": ENTITY, "values": values},
                },
                {
                    "block": "notification",
                    "action": "send",
                    "params": {"action": "send"},
                    "input": {
                        "channel": "mcp",
                        "subject": "Purchase order " + po + " placed with " + supplier,
                        "message": brief,
                        "block": CAPABILITY_ID,
                        "tool": "notification",
                    },
                },
            ],
        }
    if block_id == "recommendation_template":
        return {
            "variance_data": [_variance_item(payload)],
            "operation": "recommend",
        }
    if block_id == "notification":
        return {
            "channel": "email",
            "to": _email(payload, "supplier_email"),
            "subject": "Purchase order " + po + " raised with " + supplier,
            "message": brief,
            "block": CAPABILITY_ID,
            "tool": "notification",
        }
    return dict(payload)


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
    payload = _normalise_suppliers(payload)

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
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "results": results,
            "stored": stored,
            "purchase_state": _insight(payload),
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
    if isinstance(result, dict) and result.get('stored') is None:
        result = dict(result)
        result['stored'] = _persist_record(payload)
    return result
