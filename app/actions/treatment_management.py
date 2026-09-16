"""Treatment and clinical documentation for VetClinicOS.

Written by the factory WRITER role (codewhale exec). This handler was
authored by the coding agent (codewhale exec) in the WRITER seat.

Domain: treatments, prescriptions, procedures and observations, linked back
to the patient record, with the documenting clinician notified.

Blocks (Registry-verified, dispatched by keyword action):
  workflow        run    — the documentation pipeline with prepared steps
  document_engine parse  — the treatment note as a stored document
  capture         extract— structured fields off the note (offline, P1)
  notification    send   — the clinician notification

Scope: READS caller input, STORAGE_PATH, vendored blocks. WRITES the
treatment entity through store.save(ENTITY, ...). NEVER network I/O.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "treatment_management"
ENTITY = 'treatment_management'
BLOCK_IDS = ['workflow', 'document_engine', 'capture', 'notification']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'document_engine': 'parse', 'capture': 'extract', 'notification': 'send'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'pet_name', 'veterinarian', 'treatment_type', 'diagnosis', 'procedure_notes', 'medication', 'dosage', 'treatment_date', 'follow_up_date', 'attachment_path']


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
    """The object each bound block is handed, built from the treatment."""
    reference = _text(payload, "reference") or "unreferenced"
    pet = _text(payload, "pet_name") or "unknown patient"
    vet = _text(payload, "veterinarian") or "unassigned veterinarian"
    note = " ".join(
        part
        for part in (
            _text(payload, "treatment_type"),
            _text(payload, "diagnosis"),
            _text(payload, "medication"),
            _text(payload, "procedure_notes"),
        )
        if part
    ) or ("treatment note for " + pet)
    if block_id == "document_engine":
        return {"content": note, "output_format": "text", "use_platform_pdf": True}
    if block_id == "capture":
        return {"text": note, "ocr_engine": "scripted", "llm_provider": "none"}
    if block_id == "notification":
        return {
            "channel": "mcp",
            "message": "treatment documented for " + pet + " by " + vet,
            "block": "treatment_management",
            "tool": "notification",
            "subject": "Treatment note " + reference,
        }
    if block_id == "workflow":
        return {
            "steps": _workflow_steps(payload),
            "result": {"reference": reference, "pet_name": pet, "note": note},
        }
    return dict(payload)

def _clinical_summary(payload: Dict[str, Any]) -> str:
    """One line of clinical intent for the documented treatment."""
    parts = [
        _text(payload, "treatment_type"),
        _text(payload, "diagnosis"),
        _text(payload, "medication"),
        _text(payload, "dosage"),
    ]
    return " ".join(part for part in parts if part) or "clinical observation recorded"


def _workflow_steps(payload: Dict[str, Any]) -> list:
    """The documentation pipeline's children, each a prepared step.

    A Store workflow dispatches a child as ``block.execute(step["input"],
    step["params"])``; the child reads its operation from ``params``. An
    input-only step is answered ``Unknown action: None`` and surfaces as
    ``workflow: step_0 (event_bus): error``, so every child carries both.
    """
    reference = _text(payload, "reference") or "unreferenced"
    pet = _text(payload, "pet_name") or "unknown patient"
    vet = _text(payload, "veterinarian") or "unassigned veterinarian"
    return [
        {
            "block": "event_bus",
            "action": "publish",
            "input": {
                "topic": "treatment.documented",
                "payload": {"reference": reference, "pet_name": pet, "veterinarian": vet, "summary": _clinical_summary(payload)},
                "message": "treatment documented for " + pet,
                "channel": "mcp",
                "tool": "event_bus",
            },
            "params": {"action": "publish", "topic": "treatment.documented"},
        }
    ]


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
        result["clinical_summary"] = _clinical_summary(payload)
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
