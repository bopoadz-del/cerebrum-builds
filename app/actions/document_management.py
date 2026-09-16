"""Document management for LexManage.

Written by the factory WRITER role (codewhale exec). Authored by the coding agent in the WRITER seat:
this module is the capability's real handler, not a contract template.

Domain: Document vault: versioned storage, text extraction, full-text indexing and an audit trail per document action.

Blocks (registry-verified, dispatched by keyword action):
  storage          store            Secure storage, organization, and retrieval of legal documents with version control and full-text search.
  document_engine  parse            Secure storage, organization, and retrieval of legal documents with version control and full-text search.
  vector_search    search           Secure storage, organization, and retrieval of legal documents with version control and full-text search.
  audit            log              Secure storage, organization, and retrieval of legal documents with version control and full-text search.

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

CAPABILITY_ID = "document_management"
ENTITY = 'document_management'
BLOCK_IDS = ['storage', 'document_engine', 'vector_search', 'audit']
#: Each block's declared default action (from its block.json).
#: Blocks are action-dispatched; calling one with no action answers
#: 'Unknown action'.
BLOCK_DEFAULT_ACTIONS = {'storage': 'store', 'document_engine': 'parse', 'vector_search': 'search', 'audit': 'log'}
#: This capability's own domain columns, declared so the kernel does
#: not strip a domain field that shares a trust-scope name.
CAPABILITY_FIELDS = ['reference', 'status', 'document_title', 'document_type', 'matter_number', 'version', 'file_path', 'content_hash', 'confidentiality', 'document_owner', 'tags', 'uploaded_by', 'uploaded_at']
_INSIGHT_KEY = 'vault_state'

REQUIRED_FIELDS = ['reference', 'status', 'document_title']

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

def _document_body(payload: Dict[str, Any]) -> str:
    """The canonical text of the document this record describes."""
    return (
        "Document " + (_text(payload, "document_title") or "untitled")
        + " (type " + (_text(payload, "document_type") or "unclassified") + ")"
        + " matter " + (_text(payload, "matter_number") or "unfiled")
        + " version " + (_text(payload, "version") or "1")
        + " confidentiality " + (_text(payload, "confidentiality") or "internal")
        + " owner " + (_text(payload, "document_owner") or "vault")
        + " tags " + (_text(payload, "tags") or "none")
    )


def _document_hash(payload: Dict[str, Any]) -> str:
    """Stable digest of the stored bytes; the record carries its own proof."""
    import hashlib

    return hashlib.sha256(_document_body(payload).encode("utf-8")).hexdigest()


def _block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """The object each bound block is handed, built from the vault record."""
    reference = _text(payload, "reference") or "unreferenced"
    title = _text(payload, "document_title") or "untitled document"
    body = _document_body(payload)
    if block_id == "storage":
        # store MINTS the file_id; the handler carries the returned id into
        # the record it persists (app/store.py write) rather than assuming it.
        return {
            "filename": _text(payload, "file_path") or (reference + ".txt"),
            "content": body,
            "metadata": {
                "capability": CAPABILITY_ID,
                "document_title": title,
                "version": _text(payload, "version") or "1",
                "content_hash": _document_hash(payload),
            },
        }
    if block_id == "document_engine":
        return {
            "filename": reference + ".txt",
            "content": body,
            "input": {"reference": reference, "document_title": title},
            "file_path": _text(payload, "file_path") or None,
        }
    if block_id == "vector_search":
        query = " ".join(
            part
            for part in (
                title,
                _text(payload, "document_type"),
                _text(payload, "tags"),
                _text(payload, "matter_number"),
            )
            if part
        )
        return {
            "query": query or title,
            "collection": CAPABILITY_ID,
            "top_k": 5,
        }
    if block_id == "audit":
        return {
            "event_action": "document.upload",
            "resource": title,
            "user_id": _text(payload, "uploaded_by") or "vault",
            "category": _text(payload, "confidentiality") or "data_access",
            "details": {
                "reference": reference,
                "matter_number": _text(payload, "matter_number"),
                "version": _text(payload, "version") or "1",
                "content_hash": _document_hash(payload),
            },
            "immutable": True,
        }
    return dict(payload)


def _insight(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Vault state: the digest the record claims and its version."""
    return {
        "content_hash": _document_hash(payload),
        "version": _text(payload, "version") or "1",
        "document_type": _text(payload, "document_type") or "unclassified",
    }

def _normalise_document(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Vault normalisation: every version is explicit and hashed before storage."""
    data = dict(payload) if isinstance(payload, dict) else {}
    data["version"] = _text(data, "version") or "1"
    data["confidentiality"] = (_text(data, "confidentiality") or "internal").lower()
    if not _text(data, "content_hash"):
        data["content_hash"] = _document_hash(data)
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
    payload = _normalise_document(payload)

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
