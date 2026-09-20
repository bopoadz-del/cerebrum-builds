"""Handler for capability audit_and_access_control.

Written by the factory WRITER role (codewhale exec). Blocks are invoked through the
local dispatch runtime -- this module makes no network call.

Persistence is route-scoped (factory-grounded persist envelope): the ROUTE's
tenant-scoped save writes the request after SUCCESS; handle() is pure
dispatch and must not persist directly (Phase 2 §0.2).
"""

from __future__ import annotations

from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "audit_and_access_control"
ENTITY = 'audit_and_access_control'
BLOCK_IDS = ['audit', 'team', 'validation', 'database']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'audit': 'log', 'team': 'create_team', 'validation': 'validate_pipeline', 'database': 'query'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'actor_name', 'actor_role', 'action_type', 'entity_name', 'entity_reference', 'change_summary', 'approval_state', 'occurred_at', 'notes']


#: What each role on this platform may do. Declared as data so a change to
#: the contractor's own responsibility matrix is a change here, not a hunt
#: through route bodies.
ROLE_PERMISSIONS: Dict[str, tuple] = {
    "owner": ("approve", "certify", "amend", "read", "export"),
    "site_engineer": ("record_progress", "raise_snag", "raise_variation", "read"),
    "accounts": ("certify", "invoice", "pay", "read", "export"),
    "admin": ("read", "grant_access", "revoke_access"),
}


#: This capability's own field contract, declared here in the shape the
#: factory's spec aligner mines (``align_spec_to_handler_source`` reads a
#: ``constraints = {...}`` literal plus a ``required = [...]`` assignment off
#: the handler/route source). The harness builds its schema sample from what
#: it mines, so the payload it POSTs is assembled from the same columns the
#: model and this handler serve -- never from an empty envelope.
constraints = {'reference': {'type': 'str'}, 'status': {'type': 'str', 'allowed_values': ['open', 'in_progress', 'closed']}, 'actor_name': {'type': 'str'}, 'actor_role': {'type': 'str', 'allowed_values': ['owner', 'site_engineer', 'accounts', 'admin']}, 'action_type': {'type': 'str', 'allowed_values': ['approval', 'document_version', 'financial_change', 'access_grant', 'access_revoke']}, 'entity_name': {'type': 'str'}, 'entity_reference': {'type': 'str'}, 'change_summary': {'type': 'str'}, 'approval_state': {'type': 'str', 'allowed_values': ['pending', 'approved', 'rejected']}, 'occurred_at': {'type': 'str'}, 'notes': {'type': 'str'}}
required = ['reference', 'status', 'actor_name', 'actor_role', 'action_type']

def _domain_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The access decision and change summary this audit record stands for."""
    role = str(payload.get("actor_role") or "").strip().lower()
    permitted = ROLE_PERMISSIONS.get(role)
    return {
        "actor_name": payload.get("actor_name"),
        "actor_role": role,
        "known_role": permitted is not None,
        "permitted_actions": list(permitted or ()),
        "action_type": payload.get("action_type"),
        "approval_state": payload.get("approval_state") or "not_required",
        "may_approve": bool(permitted and "approve" in permitted),
    }


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
        try:
            res = _dispatch.execute(
                block_id, prepared, action=action, params=params
            )
        except Exception as exc:  # a block that cannot run is a refusal, not a crash
            res = {
                "status": "error",
                "block": block_id,
                "error": f"{type(exc).__name__}: {exc}",
                "ok": False,
            }
        try:
            from app.block_inputs import idempotent_refusal as _idempotent_refusal
        except ImportError:  # pragma: no cover - unit stubs / older emit
            _idempotent_refusal = None
        if _idempotent_refusal is not None:
            res = _idempotent_refusal(block_id, res, prepared) or res
        if isinstance(res, dict) and (
            res.get("status") == "error" or "error" in res
        ):
            _block_errors.append(
                "%s: %s" % (block_id, str(res.get("error") or res.get("status"))[:160])
            )
        return res
    def _impl(payload, execute=_watched):
        access = _domain_summary(payload)
        results = {}
        errors = {}
        for block_id in BLOCK_IDS:
            result = execute(
                block_id, payload, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
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
        return {"ok": True, "capability": CAPABILITY_ID, "results": results,
                "access": access}
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
    if isinstance(result, dict):
        result = dict(result)
        result.setdefault('ok', True)
        return result
    return {'ok': True, 'capability': CAPABILITY_ID, 'result': result}
