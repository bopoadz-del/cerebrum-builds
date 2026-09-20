"""Handler for capability automation_reminders_escalation.

Written by the factory WRITER role (codewhale exec). Blocks are invoked through the
local dispatch runtime -- this module makes no network call.

Persistence is route-scoped (factory-grounded persist envelope): the ROUTE's
tenant-scoped save writes the request after SUCCESS; handle() is pure
dispatch and must not persist directly (Phase 2 §0.2).
"""

from __future__ import annotations

from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "automation_reminders_escalation"
ENTITY = 'automation_reminders_escalation'
BLOCK_IDS = ['queue', 'event_bus', 'notification', 'workflow', 'recommendation_template']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'queue': 'enqueue', 'event_bus': 'publish', 'notification': 'send', 'workflow': 'run', 'recommendation_template': 'apply_template'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'job_code', 'reminder_type', 'due_date', 'threshold_count', 'actual_count', 'escalation_state', 'channel', 'recipient_email', 'message_body', 'schedule', 'summary']


#: This capability's own field contract, declared here in the shape the
#: factory's spec aligner mines (``align_spec_to_handler_source`` reads a
#: ``constraints = {...}`` literal plus a ``required = [...]`` assignment off
#: the handler/route source). The harness builds its schema sample from what
#: it mines, so the payload it POSTs is assembled from the same columns the
#: model and this handler serve -- never from an empty envelope.
constraints = {'reference': {'type': 'str'}, 'status': {'type': 'str', 'allowed_values': ['open', 'in_progress', 'closed']}, 'job_code': {'type': 'str'}, 'reminder_type': {'type': 'str', 'allowed_values': ['valuation_due', 'variation_escalation', 'snag_escalation', 'overdue_payment']}, 'due_date': {'type': 'str'}, 'threshold_count': {'type': 'int', 'min': 0, 'max': 10000}, 'actual_count': {'type': 'int', 'min': 0, 'max': 10000}, 'escalation_state': {'type': 'str', 'allowed_values': ['none', 'flagged', 'escalated']}, 'channel': {'type': 'str', 'allowed_values': ['email', 'webhook', 'slack']}, 'recipient_email': {'type': 'str'}, 'message_body': {'type': 'str'}, 'schedule': {'type': 'str', 'allowed_values': ['monthly', 'weekly', 'daily']}, 'summary': {'type': 'str'}}
required = ['reference', 'status', 'job_code', 'reminder_type']

def _domain_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The escalation decision: has the count passed the contractor's threshold?"""
    def _n(key: str) -> int:
        raw = payload.get(key)
        try:
            return int(float(raw)) if raw not in (None, "") else 0
        except (TypeError, ValueError):
            return 0

    threshold, actual = _n("threshold_count"), _n("actual_count")
    exceeded = bool(threshold) and actual >= threshold
    return {
        "job_code": payload.get("job_code"),
        "reminder_type": payload.get("reminder_type"),
        "schedule": payload.get("schedule") or "monthly",
        "due_date": payload.get("due_date"),
        "threshold_count": threshold,
        "actual_count": actual,
        "escalate": exceeded,
        "escalation_state": payload.get("escalation_state") or ("escalated" if exceeded else "none"),
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
        escalation = _domain_summary(payload)
        results = {}
        errors = {}
        steps = [{
            "block": "event_bus",
            "action": "publish",
            "input": {
                "topic": 'reminder.valuation_due',
                "payload": {"reference": payload.get("reference") or payload.get('job_code') or "record"},
                "message": 'reminder valuation_due',
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
                "escalation": escalation}
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
