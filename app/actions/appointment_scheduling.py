"""Handler for capability appointment_scheduling.

Written by the factory WRITER role (codewhale exec). Blocks are invoked through the
local dispatch runtime -- this module makes no network call.

Persistence is route-scoped (factory-grounded persist envelope): the ROUTE's
tenant-scoped save writes the request after SUCCESS; handle() is pure
dispatch and must not persist directly (Phase 2 §0.2).
"""

from __future__ import annotations

from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "appointment_scheduling"
ENTITY = 'appointment_scheduling'
BLOCK_IDS = ['workflow', 'database', 'validation', 'audit']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'database': 'query', 'validation': 'validate_pipeline', 'audit': 'log'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names would be
#: deleted before handle() ever saw it. Declaring the names here tells the
#: kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'patient_name', 'patient_email', 'scheduled_at', 'provider', 'chair_room', 'appointment_type', 'duration_minutes', 'reminder_channel', 'notes']


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
        if not isinstance(payload, dict):
            return {"ok": False, "capability": CAPABILITY_ID, "error": "payload must be an object"}
        record = dict(payload)
        record["patient_name"] = str(record.get("patient_name") or "").strip()
        scheduled = str(record.get("scheduled_at") or "").strip()
        if not record["patient_name"] or not scheduled:
            return {"ok": False, "capability": CAPABILITY_ID,
                    "error": "Missing required fields: patient_name, scheduled_at"}
        record.setdefault("duration_minutes", 30)
        record.setdefault("appointment_type", "exam")
        record["reminder_channel"] = record.get("reminder_channel") or "email"
        record["chair_room"] = str(record.get("chair_room") or "chair-1")
        record["provider"] = str(record.get("provider") or "")
        # The day-before reminder is scheduled off this booking.
        record["reminder_due_at"] = scheduled
        results = {}
        errors = {}
        steps = [{
            "block": "event_bus",
            "action": "publish",
            "input": {
                "topic": "appointment.scheduled",
                "payload": {
                    "reference": payload.get("reference") or "appointment",
                    "patient_name": record["patient_name"],
                    "scheduled_at": scheduled,
                    "chair_room": record["chair_room"],
                },
                "message": "appointment booked at the front desk",
                "channel": "mcp",
                "tool": "event_bus",
            },
        }]
        for block_id in BLOCK_IDS:
            if block_id == 'workflow':
                continue
            result = execute(
                block_id, record, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
            )
            results[block_id] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors[block_id] = str(result.get("error") or result)[:200]
        if 'workflow' in BLOCK_IDS:
            result = execute(
                'workflow',
                {'steps': steps, 'result': steps[0].get('input')},
                action=BLOCK_DEFAULT_ACTIONS.get('workflow') or 'run',
            )
            results['workflow'] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors['workflow'] = str(result.get("error") or result)[:200]
        if errors:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
                "results": results,
            }
        record["status"] = record.get("status") or "open"
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "record": record,
            "results": results,
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
    if isinstance(result, dict):
        result = dict(result)
        result.setdefault('ok', True)
        return result
    return {'ok': True, 'capability': CAPABILITY_ID, 'result': result}
