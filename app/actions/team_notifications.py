"""Handler for capability team_notifications.

Written by the factory WRITER role (codewhale exec). Blocks are invoked through the
local dispatch runtime -- this module makes no network call.

Persistence is route-scoped (factory-grounded persist envelope): the ROUTE's
tenant-scoped save writes the request after SUCCESS; handle() is pure
dispatch and must not persist directly (Phase 2 §0.2).
"""

from __future__ import annotations

from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "team_notifications"
ENTITY = 'team_notifications'
BLOCK_IDS = ['notification', 'event_bus']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'notification': 'send', 'event_bus': 'publish'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'recipient_email', 'recipient_role', 'channel', 'subject', 'message_body', 'notification_type', 'related_reference', 'send_at', 'delivery_state']


#: This capability's own field contract, declared here in the shape the
#: factory's spec aligner mines (``align_spec_to_handler_source`` reads a
#: ``constraints = {...}`` literal plus a ``required = [...]`` assignment off
#: the handler/route source). The harness builds its schema sample from what
#: it mines, so the payload it POSTs is assembled from the same columns the
#: model and this handler serve -- never from an empty envelope.
constraints = {'reference': {'type': 'str'}, 'status': {'type': 'str', 'allowed_values': ['open', 'in_progress', 'closed']}, 'recipient_email': {'type': 'str'}, 'recipient_role': {'type': 'str', 'allowed_values': ['owner', 'site_engineer', 'accounts']}, 'channel': {'type': 'str', 'allowed_values': ['email', 'slack', 'webhook']}, 'subject': {'type': 'str'}, 'message_body': {'type': 'str'}, 'notification_type': {'type': 'str', 'allowed_values': ['approval', 'valuation_due', 'overdue_item', 'snag']}, 'related_reference': {'type': 'str'}, 'send_at': {'type': 'str'}, 'delivery_state': {'type': 'str', 'allowed_values': ['queued', 'sent', 'skipped']}}
required = ['reference', 'status', 'subject', 'message_body']

def _domain_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Who is told what, on which channel, for which event."""
    return {
        "notification_type": payload.get("notification_type") or "team_message",
        "channel": payload.get("channel") or "email",
        "recipient_email": payload.get("recipient_email"),
        "recipient_role": payload.get("recipient_role"),
        "related_reference": payload.get("related_reference"),
        "subject": payload.get("subject"),
        "delivery_state": payload.get("delivery_state") or "queued",
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
        notification = _domain_summary(payload)
        results = {}
        errors = {}
        steps = [{
            "block": "event_bus",
            "action": "publish",
            "input": {
                "topic": 'notification.team_message',
                "payload": {"reference": payload.get("reference") or payload.get('related_reference') or "record"},
                "message": 'notification team_message',
                "channel": "mcp",
                "tool": "event_bus",
            },
        }]
        for block_id in BLOCK_IDS:
            if block_id in ('workflow', 'event_bus'):
                continue
            result = execute(
                block_id, payload, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
            )
            results[block_id] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors[block_id] = str(result.get("error") or result)[:200]
        if 'workflow' in BLOCK_IDS:
            result = execute(
                'workflow', {'steps': steps, 'result': (steps[0].get('input') if steps else payload)}, action=BLOCK_DEFAULT_ACTIONS.get('workflow') or 'run',
            )
            results['workflow'] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors['workflow'] = str(result.get("error") or result)[:200]
        if 'event_bus' in BLOCK_IDS:
            result = execute(
                'event_bus', steps[0]['input'], action=BLOCK_DEFAULT_ACTIONS.get('event_bus') or 'publish',
            )
            results['event_bus'] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors['event_bus'] = str(result.get("error") or result)[:200]
        if errors:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
                "results": results,
            }
        return {"ok": True, "capability": CAPABILITY_ID, "results": results,
                "notification": notification}
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
