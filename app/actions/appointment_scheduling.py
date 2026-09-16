"""Appointment scheduling for VetClinicOS.

Written by the factory WRITER role (codewhale exec). This handler was
authored by the coding agent (codewhale exec) in the WRITER seat.

Domain: booking, rescheduling and reminder tracking across veterinarians.
The booking owns the calendar slot; the reminder is a queued job; the
veterinarian is told through the notification block.

Blocks (Registry-verified, dispatched by keyword action):
  workflow     run       — the booking pipeline, every child step prepared
  queue        enqueue   — the reminder job for the slot
  notification send      — the message to owner and veterinarian
  team         create_team — the clinic workspace the booking belongs to

Scope: READS caller input, STORAGE_PATH, vendored blocks. WRITES the
appointment entity through store.save(ENTITY, ...), the queue and the
notification spool. NEVER network I/O, never a raw schema sample as a
workflow step.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "appointment_scheduling"
ENTITY = 'appointment_scheduling'
BLOCK_IDS = ['workflow', 'queue', 'notification', 'team']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'queue': 'enqueue', 'notification': 'send', 'team': 'check_permission'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'pet_name', 'owner_name', 'veterinarian', 'appointment_date', 'appointment_time', 'duration_minutes', 'visit_reason', 'room', 'appointment_status']


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
    """The object each bound block is handed, built from the booking."""
    reference = _text(payload, "reference") or "unreferenced"
    pet = _text(payload, "pet_name") or "unknown patient"
    vet = _text(payload, "veterinarian") or "unassigned veterinarian"
    slot = " ".join(
        part for part in (_text(payload, "appointment_date"), _text(payload, "appointment_time")) if part
    ) or "unscheduled"
    if block_id == "queue":
        return {
            "job_type": "appointment_reminder",
            "payload": {"reference": reference, "pet_name": pet, "slot": slot},
            "priority": 5,
        }
    if block_id == "notification":
        return {
            "channel": "email",
            "to": _email(payload, "owner_email") or "frontdesk@example.com",
            "subject": "Appointment for " + pet + " at " + slot,
            "message": pet + " is booked with " + vet + " at " + slot,
            "block": "appointment_scheduling",
            "tool": "notification",
        }
    if block_id == "team":
        # The Store team block offers create but no upsert, so a re-posted
        # booking would collide on the workspace slug. This bind is a
        # permission check instead: does this veterinarian hold the clinic
        # permission for the appointment they are being booked into?
        return {
            "user_id": vet or "clinic-vet",
            "team_id": _slug("clinic-" + reference),
            "permission": "appointment_scheduling:write",
            "role": "vet",
        }
    if block_id == "workflow":
        return {"steps": [], "result": {"reference": reference, "pet_name": pet, "slot": slot}}
    return dict(payload)

def _slug(value: str) -> str:
    """A team slug the Store team block accepts: [a-z0-9-] only."""
    return "".join(ch if ch.isalnum() else "-" for ch in str(value or "").lower()).strip("-") or "clinic"


def _slot(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The calendar slot, with its duration bounded by the schema."""
    minutes = _int(payload, "duration_minutes", 15)
    if minutes < 5:
        minutes = 5
    if minutes > 480:
        minutes = 480
    return {
        "date": _text(payload, "appointment_date"),
        "time": _text(payload, "appointment_time"),
        "duration_minutes": minutes,
        "room": _text(payload, "room") or "unassigned",
    }


def _workflow_steps(payload: Dict[str, Any]) -> list:
    """The booking pipeline's children, every one a prepared event_bus step.

    The Store workflow dispatches a child as ``block.execute(step["input"],
    step["params"])`` and the child reads its operation from ``params``. A
    step that carries only ``input`` is answered ``Unknown action: None`` —
    the step_0 (event_bus) error class. Every child is therefore prepared with
    block/action/input/params, and the first step's result is carried on the
    pipeline envelope so the workflow shim can read ``input["result"]``.
    """
    reference = _text(payload, "reference") or "unreferenced"
    pet = _text(payload, "pet_name") or "unknown patient"
    vet = _text(payload, "veterinarian") or "unassigned veterinarian"
    slot = " ".join(
        part for part in (_text(payload, "appointment_date"), _text(payload, "appointment_time")) if part
    ) or "unscheduled"
    return [
        {
            "block": "event_bus",
            "action": "publish",
            "input": {
                "topic": "appointment.scheduled",
                "payload": {"reference": reference, "pet_name": pet, "veterinarian": vet, "slot": slot},
                "message": "appointment scheduled for " + pet + " with " + vet + " at " + slot,
                "channel": "mcp",
                "tool": "event_bus",
            },
            "params": {"action": "publish", "topic": "appointment.scheduled"},
        }
    ]


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
        steps = _workflow_steps(payload)
        for block_id in BLOCK_IDS:
            if block_id in ('workflow', 'event_bus'):
                continue
            result = execute(
                block_id,
                _block_input(block_id, payload),
                action=BLOCK_DEFAULT_ACTIONS.get(block_id),
            )
            results[block_id] = result
            if (
                block_id == "team"
                and isinstance(result, dict)
                and "already exists" in str(result.get("error") or "").lower()
            ):
                # The Store team block offers create but no upsert: the
                # workspace already existing IS the desired end state for a
                # re-posted record. Recorded as a note, never hidden.
                results[block_id] = {
                    "status": "ok",
                    "block": block_id,
                    "workspace": "existing",
                    "note": "team workspace already exists for this record",
                }
                continue
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
        stored = _persist_record(payload)
        return {"ok": True, "capability": CAPABILITY_ID, "results": results, "stored": stored}
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
        result["slot"] = _slot(payload)
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
