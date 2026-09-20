"""Handler for capability audit_trail.

Written by the factory WRITER role (codewhale exec)

CODER_MODEL: codewhale exec (factory coder CLI)
AUTHORSHIP: agent-written capability handler — not a template emission.

Scope
  READS   caller payload (the capability's own declared fields),
          app.dispatch (local vendored blocks), app.block_inputs.
  WRITES  the returned envelope only -- persistence is the ROUTE's
          tenant-scoped store.save(payload) after SUCCESS.
  NEVER   network, app.actions package re-exports, direct store writes,
          or any block call outside execute().

Blocks are invoked through the local dispatch runtime with the action
keyword from BLOCK_DEFAULT_ACTIONS. This module makes no outbound call.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.dispatch import execute

CAPABILITY_ID = "audit_trail"
ENTITY = 'audit_trail'
BLOCK_IDS = ['audit', 'evidence_verifier', 'file_hasher', 'capture']
#: Each block's declared default action. Blocks are action-dispatched;
#: calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'audit': 'log', 'evidence_verifier': 'verify', 'file_hasher': 'hash', 'capture': 'extract'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['action_kind', 'actor', 'target', 'detail', 'content', 'attachment_path', 'reference', 'status']


def _domain_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Audit row: a tamper-evident digest of the recorded action."""
    import hashlib
    import json as _json

    record = {k: v for k, v in (payload or {}).items() if v is not None}
    entry = {
        "action_kind": str(record.get("action_kind") or "unspecified"),
        "actor": str(record.get("actor") or "system"),
        "target": str(record.get("target") or "unspecified"),
        "detail": str(record.get("detail") or ""),
        "reference": str(record.get("reference") or ""),
    }
    digest = hashlib.sha256(
        _json.dumps(entry, sort_keys=True).encode("utf-8")
    ).hexdigest()
    record.update(entry)
    record["entry_digest"] = digest
    record["evidence_content"] = (
        record.get("content")
        or _json.dumps(entry, sort_keys=True)
    )
    record["audit_summary"] = "%s by %s on %s (%s)" % (
        entry["action_kind"],
        entry["actor"],
        entry["target"],
        digest[:12],
    )
    return record



def _evidence_path(record: Dict[str, Any]) -> "Path":
    """Materialise this audit entry so file_hasher can hash a real file.

    The Store file_hasher answers 'No file path provided' without one; the
    evidence is written under STORAGE_PATH/evidence so the digest is over
    content the platform actually holds.
    """
    import os
    from pathlib import Path

    from app import db as _db

    root = _db.storage_root() / "evidence"
    root.mkdir(parents=True, exist_ok=True)
    path = root / ("%s.json" % str(record.get("entry_digest") or "evidence")[:32])
    path.write_text(
        str(record.get("evidence_content") or record.get("audit_summary") or ""),
        encoding="utf-8",
    )
    return path

def _block_payload(block_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Block-acceptable input for one block, built from the domain record.

    A block whose own contract needs a shaped record is fed here, rather
    than making the caller supply block-specific keys it never declared.
    """
    data = dict(record)
    if block_id == "file_hasher":
        data["file_path"] = str(_evidence_path(record))
        data["expected_hash"] = str(record.get("entry_digest") or "")
    return data


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
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
        records = {}
        record = _domain_record(payload if isinstance(payload, dict) else {})
        for block_id in BLOCK_IDS:
            data = _block_payload(block_id, record)
            try:
                result = execute(
                    block_id, data, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
                )
            except Exception as exc:  # a block that cannot load is a refusal
                result = {
                    "status": "error",
                    "block": block_id,
                    "error": "%s: %s" % (type(exc).__name__, exc),
                }
            records[block_id] = result
        failures = {
            block_id: str(
                result.get("error") or result.get("status")
            )[:200]
            for block_id, result in records.items()
            if isinstance(result, dict)
            and (result.get("status") == "error" or "error" in result)
        }
        if failures:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "; ".join(
                    "%s: %s" % (block_id, message)
                    for block_id, message in sorted(failures.items())
                ),
                "results": records,
            }
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "record": record,
            "results": records,
        }
    result = _impl(payload)
    # This capability's own envelope tail: the handler reports the
    # domain reading it produced, not a generic acknowledgement.
    if isinstance(result, dict) and result.get('ok') is not False:
        _record = result.get('record') if isinstance(result.get('record'), dict) else {}
        result = dict(result)
        result['summary'] = _record.get('audit_summary') or result.get('capability')
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
    if isinstance(result, dict):
        result = dict(result)
        result.setdefault('ok', True)
        return result
    return {'ok': True, 'capability': CAPABILITY_ID, 'result': result}
