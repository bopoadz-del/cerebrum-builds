"""Sales and orders for RetailOS.

Written by the factory WRITER role (codewhale exec). Authored by the coding agent in the WRITER seat:
this module is the capability's real handler, not a contract template.

Domain: Process sales transactions, manage orders, returns, and exchanges across in-store and online channels.

Blocks (registry-verified, dispatched by keyword action):
  database             insert           domain row written to this capability's alembic entity
  event_bus            publish          prepared publish (topic, payload, message, channel=mcp)
  workflow             run              prepared child steps, each with block + action + input
  queue                enqueue          job enqueued for the store sync worker

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

CAPABILITY_ID = "sales_and_orders"
ENTITY = 'sales_and_orders'
BLOCK_IDS = ['database', 'event_bus', 'workflow', 'queue']
#: Each block's declared default action (from its block.json / the Store
#: map). Blocks are action-dispatched; calling one with no action answers
#: 'Unknown action'.
BLOCK_DEFAULT_ACTIONS = {'database': 'insert', 'event_bus': 'publish', 'workflow': 'run', 'queue': 'enqueue'}
#: This capability's own domain columns, declared so the kernel does
#: not strip a domain field that shares a trust-scope name.
CAPABILITY_FIELDS = ['reference', 'status', 'order_number', 'customer_name', 'customer_email', 'channel', 'order_total', 'item_count', 'payment_status', 'fulfilment_status', 'order_date', 'notes']
_INSIGHT_KEY = 'order_state'

REQUIRED_FIELDS = ['reference', 'status', 'order_number', 'customer_name']

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

def _order_brief(payload: Dict[str, Any]) -> str:
    """The order line the store floor reads: who, what channel, how much."""
    parts = [
        "Order " + (_text(payload, "order_number") or "unreferenced"),
        "customer: " + (_text(payload, "customer_name") or "walk-in customer"),
        "channel: " + (_text(payload, "channel") or "in_store"),
        "total: " + str(_float(payload, "order_total", 0.0)),
        "items: " + str(_int(payload, "item_count", 0)),
        "payment: " + (_text(payload, "payment_status") or "pending"),
        "fulfilment: " + (_text(payload, "fulfilment_status") or "open"),
    ]
    return "; ".join(parts)


def _order_topic(payload: Dict[str, Any]) -> str:
    """Store bus topic for this order; always non-empty."""
    channel = (_text(payload, "channel") or "in_store").lower().replace(" ", "_")
    return "retail.order.created." + (channel or "in_store")


def _normalise_orders(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Order normalisation: every order carries a number and a channel."""
    data = dict(payload) if isinstance(payload, dict) else {}
    reference = _text(data, "reference") or "unreferenced"
    data["reference"] = reference
    data["order_number"] = _text(data, "order_number") or reference
    data["channel"] = (_text(data, "channel") or "in_store").lower()
    data["payment_status"] = (_text(data, "payment_status") or "pending").lower()
    data["fulfilment_status"] = (_text(data, "fulfilment_status") or "open").lower()
    return data


def _insight(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Order state the operator reads back off the record."""
    return {
        "order_number": _text(payload, "order_number"),
        "order_total": _float(payload, "order_total", 0.0),
        "item_count": _int(payload, "item_count", 0),
        "payment_status": _text(payload, "payment_status"),
        "fulfilment_status": _text(payload, "fulfilment_status"),
        "topic": _order_topic(payload),
    }


def _order_event_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Prepared publish input for the Store event bus (channel mcp)."""
    return {
        "topic": _order_topic(payload),
        "payload": {
            "reference": _text(payload, "reference"),
            "order_number": _text(payload, "order_number"),
            "order_total": _float(payload, "order_total", 0.0),
            "payment_status": _text(payload, "payment_status"),
        },
        "message": _order_brief(payload),
        "channel": "mcp",
        "tool": "event_bus",
    }

def _block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """The object each bound block is handed, built from the order record."""
    reference = _text(payload, "reference") or "unreferenced"
    order_number = _text(payload, "order_number") or reference
    brief = _order_brief(payload)
    values = {key: str(value) for key, value in _record(payload).items()}
    if block_id == "database":
        return {"table": ENTITY, "values": values}
    if block_id == "event_bus":
        # Prepared publish: topic, payload dict, message and the in-process
        # mcp channel. A raw schema sample here is refused by the Store bus.
        return {
            "topic": _order_topic(payload),
            "payload": {
                "reference": reference,
                "order_number": order_number,
                "order_total": _float(payload, "order_total", 0.0),
                "payment_status": _text(payload, "payment_status"),
            },
            "message": brief,
            "channel": "mcp",
            "tool": "event_bus",
        }
    if block_id == "workflow":
        # EVERY event_bus child is prepared in source (step_2 here):
        # block + action=publish + input{topic, payload, message, channel=mcp}.
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
                    "block": "event_bus",
                    "action": "publish",
                    "params": {"action": "publish"},
                    "input": {
                        "topic": _order_topic(payload),
                        "payload": {
                            "reference": reference,
                            "order_number": order_number,
                            "payment_status": _text(payload, "payment_status"),
                        },
                        "message": brief,
                        "channel": "mcp",
                        "tool": "event_bus",
                    },
                },
                {
                    "block": "queue",
                    "action": "enqueue",
                    "params": {"action": "enqueue"},
                    "input": {
                        "job_type": "sales_order_sync",
                        "queue": CAPABILITY_ID,
                        "payload": {
                            "reference": reference,
                            "order_number": order_number,
                        },
                    },
                },
            ],
        }
    if block_id == "queue":
        return {
            "job_type": "sales_order_sync",
            "queue": CAPABILITY_ID,
            "priority": 0,
            "payload": {
                "reference": reference,
                "order_number": order_number,
                "channel": _text(payload, "channel") or "in_store",
                "order_total": _float(payload, "order_total", 0.0),
            },
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
    payload = _normalise_orders(payload)

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
            "order_state": _insight(payload),
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
