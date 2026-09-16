"""Tamper-evident audit trail for VetClinicOS.

Written by the factory WRITER role (codewhale exec). This handler was
authored by the coding agent (codewhale exec) in the WRITER seat.

Domain: an immutable, searchable log of record access, modification and
financial events. The record is hashed, the hash is verified, and the event
is published on the bus — the chain is what makes it evidential.

Blocks (Registry-verified, dispatched by keyword action):
  audit             log    — the chained, immutable event
  file_hasher       hash   — SHA256 of the record as written to disk
  evidence_verifier verify — the verification of that hash
  event_bus         publish— the published audit event (prepared step)

Scope: READS caller input, STORAGE_PATH, vendored blocks. WRITES the audit
entity through store.save(ENTITY, ...), the hashed record file and the
chained event. NEVER network I/O.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "audit_trail"
ENTITY = 'audit_trail'
BLOCK_IDS = ['audit', 'file_hasher', 'evidence_verifier', 'event_bus']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'audit': 'log', 'file_hasher': 'hash', 'evidence_verifier': 'verify', 'event_bus': 'publish'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'event_type', 'entity_name', 'entity_id', 'actor', 'actor_role', 'action_taken', 'details', 'occurred_at']


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
    """The object each bound block is handed, built from the audit event."""
    reference = _text(payload, "reference") or "unreferenced"
    actor = _text(payload, "actor") or "system"
    resource = _text(payload, "entity_name") or ENTITY
    event_action = _text(payload, "action_taken") or _text(payload, "event_type") or "access"
    if block_id == "audit":
        return {
            "event_action": event_action,
            "resource": resource,
            "user_id": actor,
            "category": _text(payload, "actor_role") or "data_access",
            "details": _record(payload),
            "immutable": True,
        }
    if block_id == "file_hasher":
        return {"file_path": _hashable_path(payload), "algorithms": ["sha256"]}
    if block_id == "evidence_verifier":
        return {"input": {"reference": reference, "integrity_hash": _digest(payload)}}
    if block_id == "event_bus":
        return {
            "topic": "audit." + event_action,
            "payload": {"reference": reference, "resource": resource, "digest": _digest(payload)},
            "message": "audit event recorded for " + resource,
            "channel": "mcp",
            "tool": "event_bus",
        }
    return dict(payload)

def _hashable_path(payload: Dict[str, Any]) -> str:
    """Write the event record to disk so file_hasher hashes real bytes.

    The path lives under STORAGE_PATH: the same root the rest of the platform
    persists to, so the audit file is inspectable and restores with the DB.
    """
    import os
    from pathlib import Path

    root = Path(os.getenv("STORAGE_PATH") or "./data") / "audit"
    root.mkdir(parents=True, exist_ok=True)
    reference = _text(payload, "reference") or "unreferenced"
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in reference)
    path = root / (safe + ".json")
    path.write_text(json.dumps(_record(payload), sort_keys=True), encoding="utf-8")
    return str(path)


def _digest(payload: Dict[str, Any]) -> str:
    """SHA256 of the canonical event record — the chain link."""
    import hashlib

    blob = json.dumps(_record(payload), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


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
        result["digest"] = _digest(payload)
        result["hashable_path"] = _hashable_path(payload)
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
