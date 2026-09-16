"""Supply and medication inventory for VetClinicOS.

Written by the factory WRITER role (codewhale exec). This handler was
authored by the coding agent (codewhale exec) in the WRITER seat.

Domain: medical supplies, medications and retail stock with levels, reorder
alerting and usage tracking tied to treatments.

Blocks (Registry-verified, dispatched by keyword action):
  database        query    — the stock row for this SKU
  readiness_engine score   — how ready the shelf is against its reorder level
  notification    send     — the reorder alert
  analytics       track_event — the stock movement

Scope: READS caller input, STORAGE_PATH, vendored blocks. WRITES the
inventory entity through store.save(ENTITY, ...). NEVER network I/O.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "inventory_management"
ENTITY = 'inventory_management'
BLOCK_IDS = ['database', 'readiness_engine', 'notification', 'analytics']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'database': 'insert', 'readiness_engine': 'score', 'notification': 'send', 'analytics': 'track_event'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'item_name', 'sku', 'category', 'quantity', 'reorder_level', 'unit_cost', 'supplier', 'expiry_date']


REQUIRED_FIELDS = ["reference", "status"]


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

def _block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """The object each bound block is handed, built from the stock record."""
    item = _text(payload, "item_name") or "unlisted item"
    sku = _text(payload, "sku") or "no-sku"
    level = _int(payload, "quantity", 0)
    reorder = _int(payload, "reorder_level", 0)
    if block_id == "database":
        values = {key: str(value) for key, value in _record(payload).items()}
        values.update({key: str(value) for key, value in _stock_state(payload).items()})
        return {"table": ENTITY, "values": values}
    if block_id == "readiness_engine":
        return {
            "input": {
                "item_name": item,
                "sku": sku,
                "quantity": level,
                "reorder_level": reorder,
                "reorder_required": level <= reorder,
            },
            "reference": _text(payload, "reference"),
        }
    if block_id == "notification":
        return {
            "channel": "mcp",
            "message": item + " at " + str(level) + " units (reorder level " + str(reorder) + ")",
            "block": "inventory_management",
            "tool": "notification",
            "subject": "Reorder review for " + sku,
        }
    if block_id == "analytics":
        return {
            "metric": "inventory_level",
            "value": level,
            "name": item,
            "tags": ["inventory", sku],
            "timestamp": _text(payload, "expiry_date"),
        }
    return dict(payload)

def _stock_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Stock level against its reorder level."""
    level = _int(payload, "quantity", 0)
    reorder = _int(payload, "reorder_level", 0)
    return {
        "quantity": level,
        "reorder_level": reorder,
        "reorder_required": level <= reorder,
    }


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
        result["stock"] = _stock_state(payload)
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
    # One insert per call. _impl already persisted once its blocks succeeded,
    # so this tail re-uses that row instead of inserting a second copy: the
    # redundant insert here cost every record a third row (handler x2 + the
    # route's own save(payload)), and a duplicated invoice, treatment or
    # stock movement is a data-integrity defect, not a style nit.
    if isinstance(result, dict):
        result = dict(result)
        result.setdefault('ok', True)
        if 'stored' not in result:
            result['stored'] = _persist_record(payload)
        return result
    stored = _persist_record(payload)
    return {'ok': True, 'capability': CAPABILITY_ID, 'stored': stored, 'result': result}
