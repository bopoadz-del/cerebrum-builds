"""Handler for capability recall_reminders.

Written by the factory WRITER role (codewhale exec). Blocks are invoked through the
local dispatch runtime -- this module makes no network call.

Persistence is route-scoped (route-scoped persist envelope): the ROUTE's
tenant-scoped save writes the request after SUCCESS; handle() is pure
dispatch and must not persist directly (Phase 2 §0.2).
"""

from __future__ import annotations

from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "recall_reminders"
ENTITY = 'recall_reminders'
BLOCK_IDS = ['workflow', 'queue', 'notification', 'analytics']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'queue': 'enqueue', 'notification': 'send', 'analytics': 'track_event'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'patient_name', 'patient_email', 'recall_interval_months', 'last_visit_date', 'due_date', 'reminder_type', 'reminder_channel', 'message_body', 'delivery_state']


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
            return {"ok": False, "capability": CAPABILITY_ID,
                    "error": "payload must be an object"}
        record = dict(payload)
        name = str(record.get("patient_name") or "").strip()
        if not name:
            return {"ok": False, "capability": CAPABILITY_ID,
                    "error": "Missing required field: patient_name"}
        record["patient_name"] = name
        record["status"] = str(record.get("status") or "open")
        record["patient_email"] = str(record.get("patient_email") or "").strip()
        record["reminder_type"] = str(record.get("reminder_type") or "recall")
        record["reminder_channel"] = str(record.get("reminder_channel") or "in_app")
        record["delivery_state"] = str(record.get("delivery_state") or "queued")
        record["last_visit_date"] = str(record.get("last_visit_date") or "").strip()
        record["due_date"] = str(record.get("due_date") or "").strip()
        try:
            record["recall_interval_months"] = int(record.get("recall_interval_months") or 6)
        except (TypeError, ValueError):
            record["recall_interval_months"] = 6
        # Due-date arithmetic is declared here and evaluated by the queue/analytics
        # path below; the reminder the patient receives is the same string the
        # record keeps, so the recall list and the notification cannot drift.
        record["message_body"] = str(record.get("message_body") or (
            f"{name} is due for a {record['reminder_type'].replace('_', ' ')} "
            f"visit (every {record['recall_interval_months']} month(s)); "
            f"last seen {record['last_visit_date'] or 'not recorded'}."
        ))
        record["recall_key"] = "|".join(
            part for part in (name.lower(), record["reminder_type"], record["due_date"])
            if part
        ) or "recall"
        prepared_event = {
            "block": "event_bus",
            "action": "publish",
            "input": {
                "topic": "reminder.due",
                "payload": {"reference": record.get("reference") or record["recall_key"]},
                "message": "recall reminder due",
                "channel": "mcp",
                "tool": "event_bus",
            },
        }
        event_bus_ready = False
        try:
            _dispatch.load_block("event_bus")
            event_bus_ready = True
        except Exception:
            event_bus_ready = False
        steps = []
        if event_bus_ready:
            steps.append(prepared_event)
        steps.append({
            "block": "queue",
            "action": "enqueue",
            "input": {
                "job_type": "recall_reminder",
                "queue": "clinic-reminders",
                "payload": {
                    "reference": record.get("reference") or record["recall_key"],
                    "patient_name": name,
                    "due_date": record["due_date"],
                    "channel": record["reminder_channel"],
                },
            },
        })
        steps.append({
            "block": "notification",
            "action": "send",
            "input": {
                "channel": "mcp",
                "tool": "queue",
                "message": record["message_body"],
                "payload": {
                    "job_type": "recall_reminder",
                    "queue": "clinic-reminders",
                    "message": record["message_body"],
                },
            },
        })
        workflow_input = {
            "pipeline_id": "recall-reminders",
            "steps": steps,
            "result": (steps[0].get("input") if steps else dict(record)),
        }
        results = {}
        errors = {}
        for block_id in BLOCK_IDS:
            block_input = workflow_input if block_id == "workflow" else record
            result = execute(
                block_id, block_input, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
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
        record["metric"] = "recall_due"
        record["value"] = 1
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "recall_key": record["recall_key"],
            "event_published": bool(event_bus_ready),
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
