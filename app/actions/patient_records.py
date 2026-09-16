"""Patient (animal) records for VetClinicOS.

Written by the factory WRITER role (codewhale exec). This handler was
authored by the coding agent (codewhale exec) in the WRITER seat; the
deterministic template was replaced wholesale.

Domain: the master patient record — owner contact details, species/breed,
weight, vaccination state, allergies and clinical notes. One POST writes the
record the front desk was given.

Blocks (Registry-verified, dispatched by keyword action):
  database  query    — the patient row as it stands for this reference
  storage   store    — the record document, written under STORAGE_PATH
  knowledge ask      — the clinic's own guidance corpus, queried for the case
  memory    get      — the hot snapshot the front desk reads back

Scope: READS caller input + STORAGE_PATH + vendored blocks. WRITES the
capability's own alembic entity through store.save(ENTITY, ...) and the
local storage tree. NEVER performs network I/O or writes another tenant's
rows.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "patient_records"
ENTITY = 'patient_records'
BLOCK_IDS = ['database', 'storage', 'knowledge', 'memory']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'database': 'insert', 'storage': 'store', 'knowledge': 'ask', 'memory': 'get'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'pet_name', 'species', 'breed', 'owner_name', 'owner_email', 'owner_phone', 'date_of_birth', 'weight_kg', 'vaccination_status', 'allergies', 'clinical_notes']


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
    """The object each bound block is handed, built from the patient record."""
    reference = _text(payload, "reference") or "unreferenced"
    pet = _text(payload, "pet_name") or "unknown patient"
    owner = _text(payload, "owner_name") or "unknown owner"
    notes = _text(payload, "clinical_notes")
    if block_id == "database":
        return {
            "table": ENTITY,
            "values": {key: str(value) for key, value in _record(payload).items()},
        }
    if block_id == "storage":
        document = json.dumps(_record(payload), sort_keys=True)
        # The authoritative copy lives under STORAGE_PATH; the sealed storage
        # block additionally spools its own copy (app/offline_blocks notes why
        # the block's data_dir is not caller-controllable).
        from app.paths import storage_root

        platform_path = storage_root() / "documents" / (reference + ".json")
        platform_path.parent.mkdir(parents=True, exist_ok=True)
        platform_path.write_text(document, encoding="utf-8")
        return {
            "filename": reference + ".json",
            "content": document,
            "metadata": {
                "capability": CAPABILITY_ID,
                "pet_name": pet,
                "platform_path": str(platform_path),
            },
        }
    if block_id == "knowledge":
        return {
            "query": " ".join(part for part in (pet, _text(payload, "species"), _text(payload, "allergies"), notes) if part),
            "collection": CAPABILITY_ID,
            "top_k": 5,
        }
    if block_id == "memory":
        return {
            "key": "patient:" + reference,
            "value": {"pet_name": pet, "owner_name": owner, "status": _text(payload, "status")},
            "ttl": 3600,
        }
    return dict(payload)

def _vitals(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Weight and vaccination state as the clinic records them."""
    return {
        "weight_kg": _float(payload, "weight_kg", 0.0),
        "vaccination_status": _text(payload, "vaccination_status") or "unknown",
        "allergies": _text(payload, "allergies") or "none recorded",
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
        result["vitals"] = _vitals(payload)
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
