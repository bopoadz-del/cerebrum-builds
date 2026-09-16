"""Compliance and audit for RetailOS.

Written by the factory WRITER role (codewhale exec). Authored by the coding agent in the WRITER seat:
this module is the capability's real handler, not a contract template.

Domain: Ensure regulatory compliance with audit trails, data privacy, and secure transaction logging.

Blocks (registry-verified, dispatched by keyword action):
  audit                log              immutable audit entry
  validation           validate_pipeline control rule parsed and run over the record
  file_hasher          hash             sha256 over the evidence bundle
  evidence_verifier    verify           verification of the evidence bundle

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

CAPABILITY_ID = "compliance_and_audit"
ENTITY = 'compliance_and_audit'
BLOCK_IDS = ['audit', 'validation', 'file_hasher', 'evidence_verifier']
#: Each block's declared default action (from its block.json / the Store
#: map). Blocks are action-dispatched; calling one with no action answers
#: 'Unknown action'.
BLOCK_DEFAULT_ACTIONS = {'audit': 'log', 'validation': 'validate_pipeline', 'file_hasher': 'hash', 'evidence_verifier': 'verify'}
#: This capability's own domain columns, declared so the kernel does
#: not strip a domain field that shares a trust-scope name.
CAPABILITY_FIELDS = ['reference', 'status', 'control_id', 'regulation', 'event_type', 'actor', 'action_taken', 'evidence_ref', 'file_path', 'findings', 'occurred_at', 'severity']
_INSIGHT_KEY = 'compliance_state'

REQUIRED_FIELDS = ['reference', 'status', 'control_id']

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

def _control_rule(payload: Dict[str, Any]) -> str:
    """The control rule the validation block parses and runs for this record."""
    return (
        "def control_rule(record):\n"
        "    required = ('control_id', 'action_taken', 'actor')\n"
        "    missing = [k for k in required if not record.get(k)]\n"
        "    return {'control_id': record.get('control_id'), "
        "'missing': missing, 'ok': not missing}\n"
    )


def _evidence_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The evidence bundle the platform hashes and verifies."""
    return {
        "reference": _text(payload, "reference"),
        "control_id": _text(payload, "control_id"),
        "regulation": _text(payload, "regulation"),
        "event_type": _text(payload, "event_type"),
        "actor": _text(payload, "actor"),
        "action_taken": _text(payload, "action_taken"),
        "findings": _text(payload, "findings"),
        "severity": _text(payload, "severity"),
        "occurred_at": _text(payload, "occurred_at"),
    }


def _evidence_path(payload: Dict[str, Any]) -> str:
    """Write the evidence bundle under the one persistence root and return it.

    The file_hasher block hashes a real file: the record's own evidence, not a
    caller-supplied path that may not exist. STORAGE_PATH is the single root
    (app/paths.py), so the evidence moves with the mounted volume.
    """
    import os
    from pathlib import Path

    root = Path(os.getenv("STORAGE_PATH") or "./data") / "evidence"
    root.mkdir(parents=True, exist_ok=True)
    name = (_text(payload, "reference") or "unreferenced").replace("/", "_")
    path = root / (name + ".json")
    path.write_text(json.dumps(_evidence_record(payload), sort_keys=True), encoding="utf-8")
    return str(path)


def _evidence_digest(payload: Dict[str, Any]) -> str:
    """Digest over the evidence the record claims to carry."""
    import hashlib

    material = "|".join(
        _text(payload, name)
        for name in ("reference", "control_id", "regulation", "action_taken", "evidence_ref")
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _normalise_compliance(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Audit normalisation: every entry names a control and an actor."""
    data = dict(payload) if isinstance(payload, dict) else {}
    reference = _text(data, "reference") or "unreferenced"
    data["reference"] = reference
    data["control_id"] = _text(data, "control_id") or "unassigned-control"
    data["actor"] = _text(data, "actor") or "system"
    data["event_type"] = (_text(data, "event_type") or "control_review").lower()
    return data


def _insight(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compliance state read back off the record."""
    return {
        "control_id": _text(payload, "control_id"),
        "regulation": _text(payload, "regulation"),
        "severity": _text(payload, "severity"),
        "evidence_digest": _evidence_digest(payload),
    }

def _block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """The object each bound block is handed, built from the audit record."""
    reference = _text(payload, "reference") or "unreferenced"
    control = _text(payload, "control_id") or "unassigned-control"
    actor = _text(payload, "actor") or "system"
    action = _text(payload, "action_taken") or _text(payload, "event_type") or "control_review"
    regulation = _text(payload, "regulation") or "internal"
    if block_id == "audit":
        return {
            "event_action": action,
            "resource": control,
            "user_id": actor,
            "category": _text(payload, "severity") or "compliance",
            "details": {
                "reference": reference,
                "regulation": regulation,
                "findings": _text(payload, "findings"),
                "evidence_digest": _evidence_digest(payload),
            },
            "immutable": True,
        }
    if block_id == "validation":
        return {
            "block_id": CAPABILITY_ID,
            "code": _control_rule(payload),
            "auto": True,
            "fail_fast": False,
            "budget": 5,
        }
    if block_id == "file_hasher":
        # A real file: the evidence bundle this record writes under
        # STORAGE_PATH. A caller-supplied path is carried only when it is a
        # file on disk, otherwise the audit entry names a path nobody has.
        import os
        from pathlib import Path

        declared = _text(payload, "file_path")
        resolved = declared if declared and os.path.isfile(declared) else ""
        return {
            "file_path": resolved or _evidence_path(payload),
            "algorithms": ["sha256"],
        }
    if block_id == "evidence_verifier":
        return {
            "input": {
                "reference": reference,
                "control_id": control,
                "regulation": regulation,
                "evidence_ref": _text(payload, "evidence_ref"),
                "digest": _evidence_digest(payload),
                "report": {
                    "status": _text(payload, "status") or "open",
                    "actor": actor,
                    "action_taken": action,
                    "occurred_at": _text(payload, "occurred_at"),
                },
            }
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
    payload = _normalise_compliance(payload)

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
            "compliance_state": _insight(payload),
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
