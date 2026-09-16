"""Billing and invoicing for VetClinicOS.

Written by the factory WRITER role (codewhale exec). This handler was
authored by the coding agent (codewhale exec) in the WRITER seat.

Domain: invoices raised from treatments and services, totals calculated by
formula, payment state and the client-facing statement.

Blocks (Registry-verified, dispatched by keyword action):
  formula_executor execute — the invoice arithmetic (subtotal, tax, total)
  document_engine  parse   — the invoice document written under STORAGE_PATH
  database         query   — the invoice row as it stands
  notification     send    — the statement to the client

Scope: READS caller input, STORAGE_PATH, vendored blocks. WRITES the invoice
entity through store.save(ENTITY, ...). NEVER network I/O.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "billing_invoicing"
ENTITY = 'billing_invoicing'
BLOCK_IDS = ['formula_executor', 'document_engine', 'database', 'notification']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'formula_executor': 'execute', 'document_engine': 'parse', 'database': 'insert', 'notification': 'send'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'invoice_number', 'client_name', 'pet_name', 'line_items', 'subtotal', 'tax_rate', 'total_amount', 'payment_status', 'payment_method', 'invoice_date', 'attachment_path']


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
    """The object each bound block is handed, built from the invoice."""
    invoice = _text(payload, "invoice_number") or _text(payload, "reference") or "unreferenced"
    client = _text(payload, "client_name") or "unknown client"
    totals = _totals(payload)
    if block_id == "formula_executor":
        return {
            "formula_key": "invoice_total",
            "operation": "auto",
            "formula_description": "invoice_total = subtotal * (1 + tax_rate)",
            "input_values": {
                "subtotal": totals["subtotal"],
                "tax_rate": totals["tax_rate"],
            },
        }
    if block_id == "document_engine":
        summary = "; ".join(
            "%s: %s" % (key, totals[key]) for key in ("subtotal", "tax_rate", "total_amount")
        )
        return {
            "content": "Invoice " + invoice + " for " + client + " (" + summary + ")",
            "output_format": "text",
            "use_platform_pdf": True,
        }
    if block_id == "database":
        values = {key: str(value) for key, value in _record(payload).items()}
        values.update({key: str(value) for key, value in totals.items()})
        return {"table": ENTITY, "values": values}
    if block_id == "notification":
        return {
            "channel": "email",
            "to": _email(payload, "client_email") or "billing@example.com",
            "subject": "Invoice " + invoice,
            "message": client + " owes " + str(totals["total_amount"]),
            "block": "billing_invoicing",
            "tool": "notification",
        }
    return dict(payload)

def _line_items(payload: Dict[str, Any]) -> float:
    """Subtotal from the declared line-item summary, or the caller's own."""
    declared = _float(payload, "subtotal", -1.0)
    if declared >= 0:
        return declared
    raw = _text(payload, "line_items")
    total = 0.0
    for token in raw.replace(";", ",").split(","):
        piece = token.strip().split(":")
        if len(piece) == 2:
            total += _float({"amount": piece[1]}, "amount", 0.0)
    return total


def _totals(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoice arithmetic the formula_executor block is asked to confirm."""
    subtotal = _line_items(payload)
    rate = _float(payload, "tax_rate", 0.0)
    if rate < 0:
        rate = 0.0
    if rate > 1:
        rate = rate / 100.0
    total = _float(payload, "total_amount", 0.0) or round(subtotal * (1.0 + rate), 2)
    return {"subtotal": round(subtotal, 2), "tax_rate": rate, "total_amount": round(total, 2)}


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
        result["totals"] = _totals(payload)
        result["line_items_total"] = _line_items(payload)
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
