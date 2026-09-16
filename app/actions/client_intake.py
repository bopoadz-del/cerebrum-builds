"""Client intake for LexManage.

Written by the factory WRITER role (codewhale exec). Authored by the coding agent in the WRITER seat:
this module is the capability's real handler, not a contract template.

Domain: New-client intake: conflict screening, risk scoring, retainer and fee estimate, engagement letter and onboarding pipeline.

Blocks (registry-verified, dispatched by keyword action):
  workflow         run              Streamlined intake process for new clients, including forms, conflict checks, and client onboarding.
  formula_executor execute          Streamlined intake process for new clients, including forms, conflict checks, and client onboarding.
  validation       validate_pipeline Streamlined intake process for new clients, including forms, conflict checks, and client onboarding.
  document_engine  parse            Streamlined intake process for new clients, including forms, conflict checks, and client onboarding.

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

CAPABILITY_ID = "client_intake"
ENTITY = 'client_intake'
BLOCK_IDS = ['workflow', 'formula_executor', 'validation', 'document_engine']
#: Each block's declared default action (from its block.json).
#: Blocks are action-dispatched; calling one with no action answers
#: 'Unknown action'.
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'formula_executor': 'execute', 'validation': 'validate_pipeline', 'document_engine': 'parse'}
#: This capability's own domain columns, declared so the kernel does
#: not strip a domain field that shares a trust-scope name.
CAPABILITY_FIELDS = ['reference', 'status', 'client_name', 'client_email', 'client_phone', 'matter_type', 'referral_source', 'conflict_check', 'risk_score', 'estimated_fee', 'retainer_amount', 'document_path', 'intake_date']
_INSIGHT_KEY = 'intake_state'

REQUIRED_FIELDS = ['reference', 'status', 'client_name']

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

def _conflict_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Conflict screening state, as recorded on the intake itself."""
    declared = _text(payload, "conflict_check").lower()
    if declared in ("cleared", "clear", "none", "no conflict"):
        cleared = True
    elif declared in ("pending", "under review"):
        cleared = False
    elif declared in ("conflict", "blocked"):
        cleared = False
    else:
        cleared = False
    return {"conflict_check": declared or "pending", "conflict_cleared": cleared}


def _risk_code(payload: Dict[str, Any]) -> str:
    """The formula the risk score is computed from, executed by the block."""
    return (
        "fee_pressure = estimated_fee / retainer if retainer else estimated_fee\n"
        "result = round(min(1.0, 0.25 + 0.5 * fee_pressure + "
        "(0.25 if not conflict_cleared else 0.0)), 4)"
    )


def _intake_code(payload: Dict[str, Any]) -> str:
    """The rule set the validation block runs over this intake."""
    return (
        "def intake_rule(record):\n"
        "    missing = [k for k in ('client_name', 'matter_type') "
        "if not record.get(k)]\n"
        "    return {'control': 'client_intake', 'missing': missing, "
        "'ok': not missing}\n"
    )


def _block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """The object each bound block is handed, built from the intake record."""
    reference = _text(payload, "reference") or "unreferenced"
    client = _text(payload, "client_name") or "unnamed client"
    matter_type = _text(payload, "matter_type") or "general"
    conflict = _conflict_state(payload)
    fee = _float(payload, "estimated_fee", 0.0)
    retainer = _float(payload, "retainer_amount", 0.0)
    if block_id == "formula_executor":
        return {
            "custom_code": _risk_code(payload),
            "input_values": {
                "estimated_fee": fee,
                "retainer": retainer,
                "conflict_cleared": bool(conflict["conflict_cleared"]),
            },
            "formula_description": "client intake risk score",
        }
    if block_id == "validation":
        return {
            "block_id": CAPABILITY_ID,
            "code": _intake_code(payload),
            "auto": True,
            "fail_fast": False,
            "budget": 5,
        }
    if block_id == "document_engine":
        letter = (
            "Engagement letter for " + client + " (" + matter_type + "); "
            + "conflict check: " + conflict["conflict_check"]
            + "; estimated fee: " + str(fee)
            + "; retainer: " + str(retainer)
            + "; intake reference: " + reference
        )
        return {
            "filename": reference + ".txt",
            "content": letter,
            "input": {"reference": reference, "client_name": client},
            "document_path": _text(payload, "document_path") or None,
        }
    if block_id == "workflow":
        return {
            "steps": [
                {
                    "block": "validation",
                    "action": "validate_pipeline",
                    "params": {"action": "validate_pipeline"},
                    "input": _block_input("validation", payload),
                },
                {
                    "block": "formula_executor",
                    "action": "execute",
                    "params": {"action": "execute"},
                    "input": _block_input("formula_executor", payload),
                },
                {
                    "block": "document_engine",
                    "action": "parse",
                    "params": {"action": "parse"},
                    "input": _block_input("document_engine", payload),
                },
            ],
            "result": {
                "reference": reference,
                "client_name": client,
                "matter_type": matter_type,
                "conflict_check": conflict["conflict_check"],
                "conflict_cleared": conflict["conflict_cleared"],
                "estimated_fee": fee,
                "retainer_amount": retainer,
            },
        }
    return dict(payload)


def _insight(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Intake state the firm reads back: conflict clearance and risk."""
    state = _conflict_state(payload)
    state.update(
        {
            "risk_score": _float(payload, "risk_score", 0.0),
            "estimated_fee": _float(payload, "estimated_fee", 0.0),
            "retainer_amount": _float(payload, "retainer_amount", 0.0),
            "onboarding": "cleared" if state["conflict_cleared"] else "blocked on conflict check",
        }
    )
    return state

def _normalise_intake(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Intake normalisation: numeric money/risk fields are numbers, not strings."""
    data = dict(payload) if isinstance(payload, dict) else {}
    for name in ("risk_score", "estimated_fee", "retainer_amount"):
        if name in data and not isinstance(data[name], (int, float)):
            data[name] = _float(data, name, 0.0)
    if isinstance(data.get("risk_score"), (int, float)):
        data["risk_score"] = round(max(0.0, min(1.0, float(data["risk_score"]))), 4)
    data["conflict_check"] = (_text(data, "conflict_check") or "pending").lower()
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
    payload = _normalise_intake(payload)

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
