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


# --- patient_and_owner_records (kernel execute_action template) ---


def _patient_and_owner_records_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.patient_and_owner_records import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/patient_and_owner_records")
async def patient_and_owner_records_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("patient_and_owner_records", payload)
    CAPABILITY_ID = "patient_and_owner_records"
    handle = _patient_and_owner_records_handle
    save = lambda record: store.save("patient_and_owner_records", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("patient_and_owner_records", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'patient_name', 'species', 'owner_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'species': {'allowed_values': ['dog', 'cat', 'rabbit', 'bird', 'reptile', 'other'], 'required': True}, 'breed': {'required': False}, 'sex': {'allowed_values': ['male', 'female', 'unknown'], 'required': False}, 'age_years': {'min': 0, 'max': 60, 'required': False}, 'weight_kg': {'min': 0.0, 'max': 300.0, 'required': False}, 'microchip_id': {'required': False}, 'owner_name': {'required': True}, 'owner_email': {'format': 'email', 'required': False}, 'owner_phone': {'required': False}, 'clinical_history': {'required': False}}
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


@router.get("/patient_and_owner_records")
def patient_and_owner_records_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["patient_and_owner_records"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("patient_and_owner_records", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/patient_and_owner_records/{item_id}")
def patient_and_owner_records_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("patient_and_owner_records", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/patient_and_owner_records/{item_id}")
async def patient_and_owner_records_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "patient_and_owner_records", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_and_owner_records", 'result': result}


@router.delete("/patient_and_owner_records/{item_id}")
async def patient_and_owner_records_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "patient_and_owner_records", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_and_owner_records", 'result': result}


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
    required_fields = ['reference', 'status', 'patient_name', 'owner_name', 'appointment_type']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'owner_name': {'required': True}, 'scheduled_at': {'format': 'datetime', 'required': False}, 'appointment_type': {'allowed_values': ['wellness_exam', 'vaccination', 'surgery', 'dental', 'emergency', 'follow_up'], 'required': True}, 'veterinarian': {'required': False}, 'room': {'required': False}, 'duration_minutes': {'min': 5, 'max': 480, 'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}, 'notes': {'required': False}}
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


# --- clinical_visit_notes_and_treatment_plans (kernel execute_action template) ---


def _clinical_visit_notes_and_treatment_plans_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.clinical_visit_notes_and_treatment_plans import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/clinical_visit_notes_and_treatment_plans")
async def clinical_visit_notes_and_treatment_plans_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("clinical_visit_notes_and_treatment_plans", payload)
    CAPABILITY_ID = "clinical_visit_notes_and_treatment_plans"
    handle = _clinical_visit_notes_and_treatment_plans_handle
    save = lambda record: store.save("clinical_visit_notes_and_treatment_plans", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("clinical_visit_notes_and_treatment_plans", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'patient_name', 'diagnosis']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'visit_date': {'format': 'date', 'required': False}, 'diagnosis': {'required': True}, 'treatment_plan': {'required': False}, 'medication': {'required': False}, 'dosage_mg': {'min': 0.0, 'max': 100000.0, 'required': False}, 'administration_route': {'allowed_values': ['oral', 'subcutaneous', 'intramuscular', 'intravenous', 'topical'], 'required': False}, 'attachment_path': {'required': False}, 'prescription_notes': {'required': False}}
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


@router.get("/clinical_visit_notes_and_treatment_plans")
def clinical_visit_notes_and_treatment_plans_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["clinical_visit_notes_and_treatment_plans"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("clinical_visit_notes_and_treatment_plans", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/clinical_visit_notes_and_treatment_plans/{item_id}")
def clinical_visit_notes_and_treatment_plans_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("clinical_visit_notes_and_treatment_plans", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/clinical_visit_notes_and_treatment_plans/{item_id}")
async def clinical_visit_notes_and_treatment_plans_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "clinical_visit_notes_and_treatment_plans", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "clinical_visit_notes_and_treatment_plans", 'result': result}


@router.delete("/clinical_visit_notes_and_treatment_plans/{item_id}")
async def clinical_visit_notes_and_treatment_plans_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "clinical_visit_notes_and_treatment_plans", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "clinical_visit_notes_and_treatment_plans", 'result': result}


# --- vaccination_tracking (kernel execute_action template) ---


def _vaccination_tracking_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.vaccination_tracking import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/vaccination_tracking")
async def vaccination_tracking_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("vaccination_tracking", payload)
    CAPABILITY_ID = "vaccination_tracking"
    handle = _vaccination_tracking_handle
    save = lambda record: store.save("vaccination_tracking", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("vaccination_tracking", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'patient_name', 'vaccine_type']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'vaccine_type': {'allowed_values': ['rabies', 'distemper', 'parvovirus', 'leptospirosis', 'bordetella', 'feline_herpesvirus', 'feline_calicivirus'], 'required': True}, 'administered_on': {'format': 'date', 'required': False}, 'next_due_on': {'format': 'date', 'required': False}, 'lot_number': {'required': False}, 'administered_by': {'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}}
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


@router.get("/vaccination_tracking")
def vaccination_tracking_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["vaccination_tracking"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("vaccination_tracking", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/vaccination_tracking/{item_id}")
def vaccination_tracking_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("vaccination_tracking", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/vaccination_tracking/{item_id}")
async def vaccination_tracking_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "vaccination_tracking", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "vaccination_tracking", 'result': result}


@router.delete("/vaccination_tracking/{item_id}")
async def vaccination_tracking_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "vaccination_tracking", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "vaccination_tracking", 'result': result}


# --- billing_and_invoicing (kernel execute_action template) ---


def _billing_and_invoicing_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.billing_and_invoicing import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/billing_and_invoicing")
async def billing_and_invoicing_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("billing_and_invoicing", payload)
    CAPABILITY_ID = "billing_and_invoicing"
    handle = _billing_and_invoicing_handle
    save = lambda record: store.save("billing_and_invoicing", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("billing_and_invoicing", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'owner_name', 'service_code']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'owner_name': {'required': True}, 'service_code': {'required': True}, 'invoice_total': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'amount_paid': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'currency': {'allowed_values': ['USD', 'EUR', 'GBP', 'CAD'], 'required': False}, 'issued_on': {'format': 'date', 'required': False}, 'due_on': {'format': 'date', 'required': False}, 'payment_method': {'allowed_values': ['card', 'cash', 'insurance', 'bank_transfer'], 'required': False}, 'attachment_path': {'required': False}}
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


@router.get("/billing_and_invoicing")
def billing_and_invoicing_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["billing_and_invoicing"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("billing_and_invoicing", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/billing_and_invoicing/{item_id}")
def billing_and_invoicing_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("billing_and_invoicing", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/billing_and_invoicing/{item_id}")
async def billing_and_invoicing_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "billing_and_invoicing", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "billing_and_invoicing", 'result': result}


@router.delete("/billing_and_invoicing/{item_id}")
async def billing_and_invoicing_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "billing_and_invoicing", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "billing_and_invoicing", 'result': result}


# --- analytics_and_reporting (kernel execute_action template) ---


def _analytics_and_reporting_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.analytics_and_reporting import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/analytics_and_reporting")
async def analytics_and_reporting_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("analytics_and_reporting", payload)
    CAPABILITY_ID = "analytics_and_reporting"
    handle = _analytics_and_reporting_handle
    save = lambda record: store.save("analytics_and_reporting", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("analytics_and_reporting", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'report_name', 'metric_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'report_name': {'required': True}, 'metric_name': {'required': True}, 'metric_value': {'min': 0.0, 'max': 100000000.0, 'required': False}, 'period_start': {'format': 'date', 'required': False}, 'period_end': {'format': 'date', 'required': False}, 'appointments_count': {'min': 0, 'max': 1000000, 'required': False}, 'revenue_total': {'min': 0.0, 'max': 100000000.0, 'required': False}, 'event_type': {'required': False}}
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


@router.get("/analytics_and_reporting")
def analytics_and_reporting_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["analytics_and_reporting"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("analytics_and_reporting", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/analytics_and_reporting/{item_id}")
def analytics_and_reporting_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("analytics_and_reporting", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/analytics_and_reporting/{item_id}")
async def analytics_and_reporting_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "analytics_and_reporting", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "analytics_and_reporting", 'result': result}


@router.delete("/analytics_and_reporting/{item_id}")
async def analytics_and_reporting_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "analytics_and_reporting", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "analytics_and_reporting", 'result': result}


# --- compliance_and_audit_trail (kernel execute_action template) ---


def _compliance_and_audit_trail_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.compliance_and_audit_trail import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/compliance_and_audit_trail")
async def compliance_and_audit_trail_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("compliance_and_audit_trail", payload)
    CAPABILITY_ID = "compliance_and_audit_trail"
    handle = _compliance_and_audit_trail_handle
    save = lambda record: store.save("compliance_and_audit_trail", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("compliance_and_audit_trail", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'record_type', 'subject_ref', 'content']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'record_type': {'allowed_values': ['clinical_note', 'invoice', 'vaccination', 'consent_form'], 'required': True}, 'subject_ref': {'required': True}, 'content': {'required': True}, 'content_hash': {'required': False}, 'reviewer': {'required': False}, 'reviewed_on': {'format': 'date', 'required': False}, 'retention_until': {'format': 'date', 'required': False}}
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


@router.get("/compliance_and_audit_trail")
def compliance_and_audit_trail_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["compliance_and_audit_trail"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("compliance_and_audit_trail", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/compliance_and_audit_trail/{item_id}")
def compliance_and_audit_trail_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("compliance_and_audit_trail", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/compliance_and_audit_trail/{item_id}")
async def compliance_and_audit_trail_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "compliance_and_audit_trail", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "compliance_and_audit_trail", 'result': result}


@router.delete("/compliance_and_audit_trail/{item_id}")
async def compliance_and_audit_trail_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "compliance_and_audit_trail", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "compliance_and_audit_trail", 'result': result}


# --- client_communication_and_reminders (kernel execute_action template) ---


def _client_communication_and_reminders_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.client_communication_and_reminders import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/client_communication_and_reminders")
async def client_communication_and_reminders_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("client_communication_and_reminders", payload)
    CAPABILITY_ID = "client_communication_and_reminders"
    handle = _client_communication_and_reminders_handle
    save = lambda record: store.save("client_communication_and_reminders", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("client_communication_and_reminders", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'owner_name', 'reminder_type']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'owner_name': {'required': True}, 'owner_email': {'format': 'email', 'required': False}, 'reminder_type': {'allowed_values': ['appointment_reminder', 'vaccination_reminder', 'follow_up', 'billing_notice'], 'required': True}, 'channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}, 'scheduled_for': {'format': 'datetime', 'required': False}, 'template_name': {'required': False}, 'message_body': {'required': False}}
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


@router.get("/client_communication_and_reminders")
def client_communication_and_reminders_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["client_communication_and_reminders"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("client_communication_and_reminders", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/client_communication_and_reminders/{item_id}")
def client_communication_and_reminders_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("client_communication_and_reminders", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/client_communication_and_reminders/{item_id}")
async def client_communication_and_reminders_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "client_communication_and_reminders", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "client_communication_and_reminders", 'result': result}


@router.delete("/client_communication_and_reminders/{item_id}")
async def client_communication_and_reminders_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "client_communication_and_reminders", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "client_communication_and_reminders", 'result': result}


@router.post("/work_queue")
async def work_queue_enqueue(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
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

