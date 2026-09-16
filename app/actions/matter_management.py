"""Matter management for LexManage.

Written by the factory WRITER role (codewhale exec). Authored by the coding agent in the WRITER seat:
this module is the capability's real handler, not a contract template.

Domain: Centralized matter file: number, client, practice area, responsible attorney, stage, deadline and the matter brief.

Blocks (registry-verified, dispatched by keyword action):
  workflow         run              Centralized tracking and management of legal matters, including case details, deadlines, and associated documents.
  database         insert           Centralized tracking and management of legal matters, including case details, deadlines, and associated documents.
  document_engine  parse            Centralized tracking and management of legal matters, including case details, deadlines, and associated documents.
  notification     send             Centralized tracking and management of legal matters, including case details, deadlines, and associated documents.

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

CAPABILITY_ID = "matter_management"
ENTITY = 'matter_management'
BLOCK_IDS = ['workflow', 'database', 'document_engine', 'notification']
#: Each block's declared default action (from its block.json).
#: Blocks are action-dispatched; calling one with no action answers
#: 'Unknown action'.
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'database': 'insert', 'document_engine': 'parse', 'notification': 'send'}
#: This capability's own domain columns, declared so the kernel does
#: not strip a domain field that shares a trust-scope name.
CAPABILITY_FIELDS = ['reference', 'status', 'matter_number', 'matter_title', 'client_name', 'client_email', 'practice_area', 'responsible_attorney', 'matter_stage', 'priority', 'opened_date', 'deadline_date', 'billing_type', 'document_path']
_INSIGHT_KEY = 'matter_state'

REQUIRED_FIELDS = ['reference', 'status', 'matter_number', 'matter_title', 'client_name']

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

def _matter_brief(payload: Dict[str, Any]) -> str:
    """The matter brief every reviewer reads: who, what, when, how urgent."""
    parts = [
        "Matter " + (_text(payload, "matter_number") or "unreferenced"),
        "title: " + (_text(payload, "matter_title") or "untitled matter"),
        "client: " + (_text(payload, "client_name") or "unnamed client"),
        "practice area: " + (_text(payload, "practice_area") or "unassigned"),
        "responsible attorney: " + (_text(payload, "responsible_attorney") or "unassigned"),
        "stage: " + (_text(payload, "matter_stage") or "intake"),
        "opened: " + (_text(payload, "opened_date") or "undated"),
        "deadline: " + (_text(payload, "deadline_date") or "none recorded"),
        "billing: " + (_text(payload, "billing_type") or "hourly"),
    ]
    return "; ".join(parts)


def _deadline_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Deadline pressure as the firm records it (no clock, no guessing)."""
    deadline = _text(payload, "deadline_date")
    opened = _text(payload, "opened_date")
    stage = _text(payload, "matter_stage") or "intake"
    return {
        "deadline_date": deadline or None,
        "opened_date": opened or None,
        "matter_stage": stage,
        "deadline_recorded": bool(deadline),
        "matter_number": _text(payload, "matter_number"),
    }


def _block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """The object each bound block is handed, built from the matter record."""
    reference = _text(payload, "reference") or "unreferenced"
    number = _text(payload, "matter_number") or reference
    title = _text(payload, "matter_title") or "untitled matter"
    client = _text(payload, "client_name") or "unnamed client"
    attorney = _text(payload, "responsible_attorney") or "unassigned attorney"
    brief = _matter_brief(payload)
    if block_id == "database":
        return {
            "table": ENTITY,
            "values": {key: str(value) for key, value in _record(payload).items()},
        }
    if block_id == "document_engine":
        # The matter brief is the document this capability actually holds; a
        # caller-supplied document_path wins when the file exists on disk.
        return {
            "filename": number + ".txt",
            "content": brief,
            "input": {"reference": reference, "matter_title": title},
            "document_path": _text(payload, "document_path") or None,
        }
    if block_id == "notification":
        return {
            "channel": "email",
            "to": _email(payload, "client_email") or "matters@example.com",
            "subject": "Matter " + number + " opened: " + title,
            "message": brief,
            "block": CAPABILITY_ID,
            "tool": "notification",
        }
    if block_id == "workflow":
        # Every child is prepared: block, action, params.action and a real
        # input. The Store workflow reads the child's operation from params.
        return {
            "steps": [
                {
                    "block": "document_engine",
                    "action": "parse",
                    "params": {"action": "parse"},
                    "input": _block_input("document_engine", payload),
                },
                {
                    "block": "database",
                    "action": "insert",
                    "params": {"action": "insert"},
                    "input": _block_input("database", payload),
                },
                {
                    "block": "notification",
                    "action": "send",
                    "params": {"action": "send"},
                    "input": _block_input("notification", payload),
                },
            ],
            "result": {
                "reference": reference,
                "matter_number": number,
                "matter_title": title,
                "client_name": client,
                "responsible_attorney": attorney,
                "summary": brief,
            },
        }
    return dict(payload)


def _insight(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Matter state the firm reads back off the record."""
    return _deadline_state(payload)

def _normalise_matter(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Matter normalisation: the file always has a number, a title and a stage."""
    data = dict(payload) if isinstance(payload, dict) else {}
    reference = _text(data, "reference") or "unreferenced"
    data["reference"] = reference
    data["matter_number"] = _text(data, "matter_number") or reference
    data["matter_title"] = _text(data, "matter_title") or ("Matter " + reference)
    data["matter_stage"] = (_text(data, "matter_stage") or "intake").lower()
    data["priority"] = (_text(data, "priority") or "normal").lower()
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
    payload = _normalise_matter(payload)

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
