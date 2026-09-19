"""HTTP surface for the platform's kernels and capabilities.

Kernel routes publish each build role's job. Capability routes run
entirely in-process: the handler dispatches to a vendored block and
the result is persisted locally. No outbound call.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app import jobs, store
from app.domain_ops import perform as perform_domain
from app.kernel_bridge import run_capability

router = APIRouter()


@router.get("/jobs")
def list_jobs() -> Dict[str, Any]:
    """Roster of every kernel job description."""
    return {"jobs": jobs.JOBS}


@router.get("/catalog")
def catalog() -> Dict[str, Any]:
    """COLLECTOR — Binding surveyor."""
    return jobs.CATALOG


@router.get("/inventory")
def inventory() -> Dict[str, Any]:
    """CLONER — Block stocker. Pinned vendor lock, read live."""
    return jobs.inventory()


@router.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    """WRITER — Platform manufacturer. Capability HTTP surface."""
    return {"items": jobs.CAPABILITIES}


@router.get("/gates")
def gates() -> Dict[str, Any]:
    """TESTER — Acceptance inspector. Coverage only; does not run tests."""
    return jobs.GATES


@router.get("/provenance")
def provenance() -> Dict[str, Any]:
    """STORE_MANAGER — Store registrar. Clone register and provenance."""
    return jobs.provenance()


# --- patient_visit_records (kernel execute_action template) ---


def _patient_visit_records_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.patient_visit_records import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/patient_visit_records")
async def patient_visit_records_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("patient_visit_records", payload)
    CAPABILITY_ID = "patient_visit_records"
    handle = _patient_visit_records_handle
    save = lambda record: store.save("patient_visit_records", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("patient_visit_records", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'patient_name', 'tooth', 'procedure']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'tooth': {'required': True}, 'procedure': {'required': True}, 'fee': {'min': 0.0, 'max': 100000.0, 'required': False}, 'visit_date': {'format': 'date', 'required': False}, 'provider': {'required': False}, 'clinical_notes': {'required': False}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/patient_visit_records")
def patient_visit_records_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["patient_visit_records"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("patient_visit_records", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/patient_visit_records/{item_id}")
def patient_visit_records_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("patient_visit_records", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/patient_visit_records/{item_id}")
async def patient_visit_records_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "patient_visit_records", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_visit_records", 'result': result}


@router.delete("/patient_visit_records/{item_id}")
async def patient_visit_records_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "patient_visit_records", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_visit_records", 'result': result}


# --- appointment_scheduling (kernel execute_action template) ---


def _appointment_scheduling_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.appointment_scheduling import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/appointment_scheduling")
async def appointment_scheduling_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("appointment_scheduling", payload)
    CAPABILITY_ID = "appointment_scheduling"
    handle = _appointment_scheduling_handle
    save = lambda record: store.save("appointment_scheduling", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("appointment_scheduling", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'patient_name', 'appointment_type']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'patient_email': {'format': 'email', 'required': False}, 'scheduled_at': {'format': 'datetime', 'required': False}, 'provider': {'required': False}, 'chair_room': {'required': False}, 'appointment_type': {'allowed_values': ['exam', 'hygiene', 'treatment', 'follow_up', 'emergency'], 'required': True}, 'duration_minutes': {'min': 5, 'max': 480, 'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}, 'notes': {'required': False}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/appointment_scheduling")
def appointment_scheduling_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["appointment_scheduling"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("appointment_scheduling", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/appointment_scheduling/{item_id}")
def appointment_scheduling_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("appointment_scheduling", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/appointment_scheduling/{item_id}")
async def appointment_scheduling_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "appointment_scheduling", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "appointment_scheduling", 'result': result}


@router.delete("/appointment_scheduling/{item_id}")
async def appointment_scheduling_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "appointment_scheduling", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "appointment_scheduling", 'result': result}


# --- todays_appointment_list (kernel execute_action template) ---


def _todays_appointment_list_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.todays_appointment_list import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/todays_appointment_list")
async def todays_appointment_list_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("todays_appointment_list", payload)
    CAPABILITY_ID = "todays_appointment_list"
    handle = _todays_appointment_list_handle
    save = lambda record: store.save("todays_appointment_list", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("todays_appointment_list", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'list_date', 'patient_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'list_date': {'format': 'date', 'required': True}, 'patient_name': {'required': True}, 'provider': {'required': False}, 'procedure': {'required': False}, 'appointment_time': {'format': 'time', 'required': False}, 'appointment_status': {'allowed_values': ['scheduled', 'checked_in', 'completed', 'cancelled'], 'required': False}, 'chair_room': {'required': False}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/todays_appointment_list")
def todays_appointment_list_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["todays_appointment_list"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("todays_appointment_list", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/todays_appointment_list/{item_id}")
def todays_appointment_list_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("todays_appointment_list", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/todays_appointment_list/{item_id}")
async def todays_appointment_list_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "todays_appointment_list", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "todays_appointment_list", 'result': result}


@router.delete("/todays_appointment_list/{item_id}")
async def todays_appointment_list_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "todays_appointment_list", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "todays_appointment_list", 'result': result}


# --- day_before_email_reminders (kernel execute_action template) ---


def _day_before_email_reminders_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.day_before_email_reminders import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/day_before_email_reminders")
async def day_before_email_reminders_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("day_before_email_reminders", payload)
    CAPABILITY_ID = "day_before_email_reminders"
    handle = _day_before_email_reminders_handle
    save = lambda record: store.save("day_before_email_reminders", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("day_before_email_reminders", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'patient_name', 'patient_email', 'reminder_date']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'patient_email': {'format': 'email', 'required': True}, 'reminder_date': {'format': 'date', 'required': True}, 'appointment_at': {'format': 'datetime', 'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}, 'message_body': {'required': False}, 'delivery_state': {'allowed_values': ['queued', 'sent', 'skipped', 'cancelled'], 'required': False}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/day_before_email_reminders")
def day_before_email_reminders_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["day_before_email_reminders"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("day_before_email_reminders", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/day_before_email_reminders/{item_id}")
def day_before_email_reminders_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("day_before_email_reminders", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/day_before_email_reminders/{item_id}")
async def day_before_email_reminders_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "day_before_email_reminders", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "day_before_email_reminders", 'result': result}


@router.delete("/day_before_email_reminders/{item_id}")
async def day_before_email_reminders_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "day_before_email_reminders", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "day_before_email_reminders", 'result': result}


# --- patient_directory (kernel execute_action template) ---


def _patient_directory_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.patient_directory import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/patient_directory")
async def patient_directory_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("patient_directory", payload)
    CAPABILITY_ID = "patient_directory"
    handle = _patient_directory_handle
    save = lambda record: store.save("patient_directory", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("patient_directory", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'patient_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'patient_email': {'format': 'email', 'required': False}, 'patient_phone': {'required': False}, 'date_of_birth': {'format': 'date', 'required': False}, 'primary_provider': {'required': False}, 'notes': {'required': False}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/patient_directory")
def patient_directory_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["patient_directory"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("patient_directory", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/patient_directory/{item_id}")
def patient_directory_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("patient_directory", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/patient_directory/{item_id}")
async def patient_directory_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "patient_directory", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_directory", 'result': result}


@router.delete("/patient_directory/{item_id}")
async def patient_directory_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "patient_directory", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_directory", 'result': result}


# --- clinical_history_search (kernel execute_action template) ---


def _clinical_history_search_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.clinical_history_search import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/clinical_history_search")
async def clinical_history_search_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("clinical_history_search", payload)
    CAPABILITY_ID = "clinical_history_search"
    handle = _clinical_history_search_handle
    save = lambda record: store.save("clinical_history_search", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("clinical_history_search", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'patient_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'tooth': {'required': False}, 'procedure': {'required': False}, 'provider': {'required': False}, 'visit_date': {'format': 'date', 'required': False}, 'date_from': {'format': 'date', 'required': False}, 'date_to': {'format': 'date', 'required': False}, 'search_notes': {'required': False}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/clinical_history_search")
def clinical_history_search_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["clinical_history_search"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("clinical_history_search", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/clinical_history_search/{item_id}")
def clinical_history_search_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("clinical_history_search", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/clinical_history_search/{item_id}")
async def clinical_history_search_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "clinical_history_search", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "clinical_history_search", 'result': result}


@router.delete("/clinical_history_search/{item_id}")
async def clinical_history_search_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "clinical_history_search", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "clinical_history_search", 'result': result}


# --- role_based_access (kernel execute_action template) ---


def _role_based_access_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.role_based_access import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/role_based_access")
async def role_based_access_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("role_based_access", payload)
    CAPABILITY_ID = "role_based_access"
    handle = _role_based_access_handle
    save = lambda record: store.save("role_based_access", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("role_based_access", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'staff_name', 'staff_role']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'staff_name': {'required': True}, 'staff_email': {'format': 'email', 'required': False}, 'staff_role': {'allowed_values': ['dentist', 'hygienist', 'receptionist', 'admin'], 'required': True}, 'permission_scope': {'required': False}, 'active_from': {'format': 'date', 'required': False}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/role_based_access")
def role_based_access_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["role_based_access"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("role_based_access", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/role_based_access/{item_id}")
def role_based_access_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("role_based_access", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/role_based_access/{item_id}")
async def role_based_access_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "role_based_access", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "role_based_access", 'result': result}


@router.delete("/role_based_access/{item_id}")
async def role_based_access_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "role_based_access", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "role_based_access", 'result': result}


@router.post("/work_queue")
async def work_queue_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    result = await perform_domain(
        "enqueue", str((payload or {}).get("capability_id") or ""), payload or {}
    )
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'result': result}


@router.post("/work_queue/{item_id}/process")
async def work_queue_process(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    result = await perform_domain("process", "", {"id": item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'result': result}


@router.get("/work_queue")
def work_queue_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app import work_queue as _work_queue
    return {"items": _work_queue.list_all()}
