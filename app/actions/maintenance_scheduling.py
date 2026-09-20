"""Handler for capability maintenance_scheduling.

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


def _as_int(value: Any, default: int = 0) -> int:
    """Coerce a caller value to int without ever raising.

    The capability's own schema samples a column the platform does not type
    as a string, so a non-numeric value is a legitimate request for those
    columns. The reading degrades to the default instead of becoming a 500.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    """Coerce a caller value to float without ever raising."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

CAPABILITY_ID = "maintenance_scheduling"
ENTITY = 'maintenance_scheduling'
BLOCK_IDS = ['estate_maintenance', 'readiness_engine', 'analytics', 'audit']
#: Each block's declared default action. Blocks are action-dispatched;
#: calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'estate_maintenance': 'plan_work', 'readiness_engine': 'score', 'analytics': 'track_event', 'audit': 'log'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['title', 'vehicle_reference', 'schedule_kind', 'due_date', 'due_mileage', 'workshop', 'downtime_days', 'estimated_cost', 'reference', 'status']


def _days_until(due: Any) -> int:
    try:
        from datetime import date

        return (date.fromisoformat(str(due)[:10]) - date.today()).days
    except (TypeError, ValueError):
        return 0


def _domain_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Preventive maintenance schedule row with its due posture."""
    record = {k: v for k, v in (payload or {}).items() if v is not None}
    kind = str(record.get("schedule_kind") or "date").strip().lower()
    record["schedule_kind"] = kind if kind in ("date", "mileage") else "date"
    days = _days_until(record.get("due_date"))
    record["days_until_due"] = days
    record["reminder_due"] = days <= 14
    record["downtime_cost"] = round(
        _as_float(record.get("estimated_cost") or 0)
        * max(_as_int(record.get("downtime_days") or 0), 0),
        2,
    )
    record["readiness_checklist"] = {
        "workshop_booked": bool(record.get("workshop")),
        "mileage_recorded": record.get("due_mileage") is not None,
        "schedule_kind_declared": bool(record.get("schedule_kind")),
    }
    record["maintenance_summary"] = "%s for %s (%s, due %s)" % (
        record.get("title") or "service job",
        record.get("vehicle_reference") or "vehicle",
        record["schedule_kind"],
        record.get("due_date") or "unscheduled",
    )
    return record


def _prepared_event_steps(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    topic = "maintenance.%s" % ("due" if record.get("reminder_due") else "scheduled")
    message = str(record.get("maintenance_summary") or "maintenance scheduled")
    payload = {
        "reference": record.get("reference") or "maintenance_scheduling",
        "vehicle_reference": record.get("vehicle_reference") or "",
        "title": record.get("title") or "",
        "days_until_due": record.get("days_until_due") or 0,
    }
    return [
        {
            "block": "event_bus",
            "action": "publish",
            # The Store workflow passes step["params"] through to the child
            # block; the step-level action is the factory contract, and the
            # param copy is what the event_bus child actually dispatches on.
            "params": {"action": "publish"},
            "input": {
                "topic": topic,
                "payload": dict(payload),
                "message": message,
                "channel": "mcp",
                "tool": "event_bus",
            },
        },
    ]


def _email_notice(record: Dict[str, Any]) -> Dict[str, str]:
    """Maintenance-due reminder, queued for the mail relay."""
    message = str(record.get("maintenance_summary") or "maintenance scheduled")
    reminder = bool(record.get("reminder_due"))
    return {
        "to": "workshop@example.com",
        "role": "branch_manager",
        "subject": "%s %s" % (
            "Maintenance due" if reminder else "Maintenance scheduled",
            record.get("reference") or "",
        ),
        "body": message,
        "reference": str(record.get("reference") or ""),
    }

def _block_payload(block_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Block-acceptable input for one block, built from the domain record.

    A block whose own contract needs a shaped record is fed here, rather
    than making the caller supply block-specific keys it never declared.
    """
    data = dict(record)
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
        errors = {}
        record = _domain_record(payload if isinstance(payload, dict) else {})

        for block_id in BLOCK_IDS:
            if block_id in ("workflow", "event_bus"):
                continue
            try:
                result = execute(
                    block_id, _block_payload(block_id, record),
                    action=BLOCK_DEFAULT_ACTIONS.get(block_id)
                )
            except Exception as exc:  # a block that cannot load is a refusal
                result = {
                    "status": "error",
                    "block": block_id,
                    "error": "%s: %s" % (type(exc).__name__, exc),
                }
            records[block_id] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors[block_id] = str(result.get("error") or result)[:200]

        email_queued = False
        try:
            from app.notifications import queue_email

            queue_email(**_email_notice(record))
            email_queued = True
        except Exception as exc:  # the notice is recorded, never silently dropped
            errors["email"] = "%s: %s" % (type(exc).__name__, exc)

        steps = _prepared_event_steps(record)
        pipeline = dict(record)
        pipeline["steps"] = steps
        pipeline["result"] = dict(steps[0]["input"]) if steps else dict(record)

        if "workflow" in BLOCK_IDS:
            try:
                result = execute(
                    "workflow", dict(pipeline),
                    action=BLOCK_DEFAULT_ACTIONS.get("workflow") or "run",
                )
            except Exception as exc:
                result = {
                    "status": "error",
                    "block": "workflow",
                    "error": "%s: %s" % (type(exc).__name__, exc),
                }
            records["workflow"] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors["workflow"] = str(result.get("error") or result)[:200]

        if "event_bus" in BLOCK_IDS:
            try:
                result = execute(
                    "event_bus", dict(steps[0]["input"]),
                    action=BLOCK_DEFAULT_ACTIONS.get("event_bus") or "publish",
                )
            except Exception as exc:
                result = {
                    "status": "error",
                    "block": "event_bus",
                    "error": "%s: %s" % (type(exc).__name__, exc),
                }
            records["event_bus"] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors["event_bus"] = str(result.get("error") or result)[:200]

        if errors:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "; ".join(
                    "%s: %s" % (block_id, message)
                    for block_id, message in sorted(errors.items())
                ),
                "results": records,
            }
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "record": record,
            "steps": steps,
            "email_queued": email_queued,
            "results": records,
        }
    result = _impl(payload)
    # This capability's own envelope tail: the handler reports the
    # domain reading it produced, not a generic acknowledgement.
    if isinstance(result, dict) and result.get('ok') is not False:
        _record = result.get('record') if isinstance(result.get('record'), dict) else {}
        result = dict(result)
        result['summary'] = _record.get('maintenance_summary') or result.get('capability')
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
