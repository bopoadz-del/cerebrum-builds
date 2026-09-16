"""Inventory management for RetailOS.

Written by the factory WRITER role (codewhale exec). Authored by the coding agent in the WRITER seat:
this module is the capability's real handler, not a contract template.

Domain: Track stock levels across locations, manage SKUs, and automate reorder points to prevent stockouts and overstock.

Blocks (registry-verified, dispatched by keyword action):
  database             insert           domain row written to this capability's alembic entity
  workflow             run              prepared child steps, each with block + action + input
  notification         send             operator notice (in-process mcp channel offline)
  validation           validate_pipeline control rule parsed and run over the record

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

CAPABILITY_ID = "inventory_management"
ENTITY = 'inventory_management'
BLOCK_IDS = ['database', 'workflow', 'notification', 'validation']
#: Each block's declared default action (from its block.json / the Store
#: map). Blocks are action-dispatched; calling one with no action answers
#: 'Unknown action'.
BLOCK_DEFAULT_ACTIONS = {'database': 'insert', 'workflow': 'run', 'notification': 'send', 'validation': 'validate_pipeline'}
#: This capability's own domain columns, declared so the kernel does
#: not strip a domain field that shares a trust-scope name.
CAPABILITY_FIELDS = ['reference', 'status', 'sku', 'product_name', 'location', 'quantity_on_hand', 'reorder_point', 'unit_cost', 'supplier_name', 'category', 'movement_type', 'last_counted_date']
_INSIGHT_KEY = 'stock_state'

REQUIRED_FIELDS = ['reference', 'status', 'sku', 'product_name']

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

def _stock_brief(payload: Dict[str, Any]) -> str:
    """The replenishment line every operator reads: what, where, how many."""
    parts = [
        "SKU " + (_text(payload, "sku") or "unassigned-sku"),
        "product: " + (_text(payload, "product_name") or "unnamed product"),
        "location: " + (_text(payload, "location") or "main store"),
        "on hand: " + str(_int(payload, "quantity_on_hand", 0)),
        "reorder point: " + str(_int(payload, "reorder_point", 0)),
        "movement: " + (_text(payload, "movement_type") or "count"),
    ]
    return "; ".join(parts)


def _reorder_needed(payload: Dict[str, Any]) -> bool:
    """True when the count is at or below the recorded reorder point."""
    on_hand = _int(payload, "quantity_on_hand", 0)
    point = _int(payload, "reorder_point", 0)
    return point > 0 and on_hand <= point


def _reorder_rule(payload: Dict[str, Any]) -> str:
    """The control rule the validation block parses and runs for this SKU."""
    return (
        "def control_rule(record):\n"
        "    required = ('sku', 'product_name', 'quantity_on_hand')\n"
        "    missing = [k for k in required if record.get(k) in (None, '')]\n"
        "    return {'sku': record.get('sku'), 'missing': missing,"
        " 'ok': not missing}\n"
    )


def _normalise_inventory(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Stock normalisation: every movement has a SKU, a location and a count."""
    data = dict(payload) if isinstance(payload, dict) else {}
    reference = _text(data, "reference") or "unreferenced"
    data["reference"] = reference
    data["sku"] = _text(data, "sku") or reference
    data["location"] = _text(data, "location") or "main store"
    data["movement_type"] = (_text(data, "movement_type") or "count").lower()
    return data


def _insight(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Stock state the operator reads back off the record."""
    return {
        "sku": _text(payload, "sku"),
        "quantity_on_hand": _int(payload, "quantity_on_hand", 0),
        "reorder_point": _int(payload, "reorder_point", 0),
        "reorder_needed": _reorder_needed(payload),
    }

def _block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """The object each bound block is handed, built from the stock record."""
    reference = _text(payload, "reference") or "unreferenced"
    name = _text(payload, "product_name") or "unnamed product"
    location = _text(payload, "location") or "main store"
    brief = _stock_brief(payload)
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
                        "subject": "Reorder review for " + name,
                        "message": brief,
                        "block": CAPABILITY_ID,
                        "tool": "notification",
                    },
                },
            ],
        }
    if block_id == "notification":
        # No operator mailbox is declared on this record: the mcp channel is
        # the in-process one prepare_block_input settles on.
        return {
            "channel": "email",
            "to": "",
            "subject": "Stock review: " + name + " at " + location,
            "message": brief,
            "block": CAPABILITY_ID,
            "tool": "notification",
        }
    if block_id == "validation":
        return {
            "block_id": CAPABILITY_ID,
            "code": _reorder_rule(payload),
            "auto": True,
            "fail_fast": False,
            "budget": 5,
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
    payload = _normalise_inventory(payload)

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
            "stock_state": _insight(payload),
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
