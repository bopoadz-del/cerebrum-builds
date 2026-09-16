"""HTTP surface for the platform's kernels and capabilities.

Kernel routes publish each build role's job. Capability routes run
entirely in-process: the handler dispatches to a vendored block and
the result is persisted locally. No outbound call.

Persistence is exactly one row per POST. The handler writes the domain
record; the route then commits the request through ``store.save_request``,
which returns the row the handler already wrote when it carries the
request's values instead of inserting a second copy
(app/store.py::save_request). ``save(payload)`` is still the route's own
write: it inserts whenever the handler stored nothing.
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


# --- patient_records (kernel execute_action template) ---


def _patient_records_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.patient_records import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/patient_records")
async def patient_records_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("patient_records", payload)
    CAPABILITY_ID = "patient_records"
    handle = _patient_records_handle
    save = lambda record: store.save_request("patient_records", record, result)
    list_all = lambda: store.list_all("patient_records")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'pet_name', 'owner_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'pet_name': {'required': True}, 'species': {'required': False}, 'breed': {'required': False}, 'owner_name': {'required': True}, 'owner_email': {'required': False}, 'owner_phone': {'required': False}, 'date_of_birth': {'required': False}, 'weight_kg': {'min': 0.0, 'max': 500.0, 'required': False}, 'vaccination_status': {'required': False}, 'allergies': {'required': False}, 'clinical_notes': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/patient_records")
def patient_records_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["patient_records"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("patient_records",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/patient_records/{item_id}")
def patient_records_get(item_id: int) -> Dict[str, Any]:
    record = store.get("patient_records", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/patient_records/{item_id}")
async def patient_records_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "patient_records", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_records", 'result': result}


@router.delete("/patient_records/{item_id}")
async def patient_records_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "patient_records", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_records", 'result': result}


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
    require_platform_token(request)
    reject_invalid_payload("appointment_scheduling", payload)
    CAPABILITY_ID = "appointment_scheduling"
    handle = _appointment_scheduling_handle
    save = lambda record: store.save_request("appointment_scheduling", record, result)
    list_all = lambda: store.list_all("appointment_scheduling")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'pet_name', 'veterinarian']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'pet_name': {'required': True}, 'owner_name': {'required': False}, 'veterinarian': {'required': True}, 'appointment_date': {'required': False}, 'appointment_time': {'required': False}, 'duration_minutes': {'min': 5, 'max': 480, 'required': False}, 'visit_reason': {'required': False}, 'room': {'required': False}, 'appointment_status': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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
        return store.query("appointment_scheduling",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/appointment_scheduling/{item_id}")
def appointment_scheduling_get(item_id: int) -> Dict[str, Any]:
    record = store.get("appointment_scheduling", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/appointment_scheduling/{item_id}")
async def appointment_scheduling_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "appointment_scheduling", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "appointment_scheduling", 'result': result}


@router.delete("/appointment_scheduling/{item_id}")
async def appointment_scheduling_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "appointment_scheduling", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "appointment_scheduling", 'result': result}


# --- treatment_management (kernel execute_action template) ---


def _treatment_management_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.treatment_management import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/treatment_management")
async def treatment_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("treatment_management", payload)
    CAPABILITY_ID = "treatment_management"
    handle = _treatment_management_handle
    save = lambda record: store.save_request("treatment_management", record, result)
    list_all = lambda: store.list_all("treatment_management")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'pet_name', 'veterinarian']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'pet_name': {'required': True}, 'veterinarian': {'required': True}, 'treatment_type': {'required': False}, 'diagnosis': {'required': False}, 'procedure_notes': {'required': False}, 'medication': {'required': False}, 'dosage': {'required': False}, 'treatment_date': {'required': False}, 'follow_up_date': {'required': False}, 'attachment_path': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/treatment_management")
def treatment_management_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["treatment_management"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("treatment_management",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/treatment_management/{item_id}")
def treatment_management_get(item_id: int) -> Dict[str, Any]:
    record = store.get("treatment_management", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/treatment_management/{item_id}")
async def treatment_management_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "treatment_management", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "treatment_management", 'result': result}


@router.delete("/treatment_management/{item_id}")
async def treatment_management_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "treatment_management", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "treatment_management", 'result': result}


# --- billing_invoicing (kernel execute_action template) ---


def _billing_invoicing_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.billing_invoicing import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/billing_invoicing")
async def billing_invoicing_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("billing_invoicing", payload)
    CAPABILITY_ID = "billing_invoicing"
    handle = _billing_invoicing_handle
    save = lambda record: store.save_request("billing_invoicing", record, result)
    list_all = lambda: store.list_all("billing_invoicing")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'invoice_number', 'client_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'invoice_number': {'required': True}, 'client_name': {'required': True}, 'pet_name': {'required': False}, 'line_items': {'required': False}, 'subtotal': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'tax_rate': {'min': 0.0, 'max': 1.0, 'required': False}, 'total_amount': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'payment_status': {'required': False}, 'payment_method': {'required': False}, 'invoice_date': {'required': False}, 'attachment_path': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/billing_invoicing")
def billing_invoicing_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["billing_invoicing"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("billing_invoicing",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/billing_invoicing/{item_id}")
def billing_invoicing_get(item_id: int) -> Dict[str, Any]:
    record = store.get("billing_invoicing", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/billing_invoicing/{item_id}")
async def billing_invoicing_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "billing_invoicing", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "billing_invoicing", 'result': result}


@router.delete("/billing_invoicing/{item_id}")
async def billing_invoicing_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "billing_invoicing", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "billing_invoicing", 'result': result}


# --- inventory_management (kernel execute_action template) ---


def _inventory_management_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.inventory_management import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/inventory_management")
async def inventory_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("inventory_management", payload)
    CAPABILITY_ID = "inventory_management"
    handle = _inventory_management_handle
    save = lambda record: store.save_request("inventory_management", record, result)
    list_all = lambda: store.list_all("inventory_management")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'item_name', 'sku']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'item_name': {'required': True}, 'sku': {'required': True}, 'category': {'required': False}, 'quantity': {'min': 0, 'max': 1000000, 'required': False}, 'reorder_level': {'min': 0, 'max': 100000, 'required': False}, 'unit_cost': {'min': 0.0, 'max': 100000.0, 'required': False}, 'supplier': {'required': False}, 'expiry_date': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/inventory_management")
def inventory_management_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["inventory_management"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("inventory_management",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/inventory_management/{item_id}")
def inventory_management_get(item_id: int) -> Dict[str, Any]:
    record = store.get("inventory_management", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/inventory_management/{item_id}")
async def inventory_management_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "inventory_management", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "inventory_management", 'result': result}


@router.delete("/inventory_management/{item_id}")
async def inventory_management_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "inventory_management", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "inventory_management", 'result': result}


# --- audit_trail (kernel execute_action template) ---


def _audit_trail_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.audit_trail import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/audit_trail")
async def audit_trail_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("audit_trail", payload)
    CAPABILITY_ID = "audit_trail"
    handle = _audit_trail_handle
    save = lambda record: store.save_request("audit_trail", record, result)
    list_all = lambda: store.list_all("audit_trail")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'event_type', 'actor']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'event_type': {'required': True}, 'entity_name': {'required': False}, 'entity_id': {'required': False}, 'actor': {'required': True}, 'actor_role': {'required': False}, 'action_taken': {'required': False}, 'details': {'required': False}, 'occurred_at': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/audit_trail")
def audit_trail_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["audit_trail"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("audit_trail",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/audit_trail/{item_id}")
def audit_trail_get(item_id: int) -> Dict[str, Any]:
    record = store.get("audit_trail", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/audit_trail/{item_id}")
async def audit_trail_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "audit_trail", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "audit_trail", 'result': result}


@router.delete("/audit_trail/{item_id}")
async def audit_trail_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "audit_trail", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "audit_trail", 'result': result}


# --- role_management (kernel execute_action template) ---


def _role_management_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.role_management import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/role_management")
async def role_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("role_management", payload)
    CAPABILITY_ID = "role_management"
    handle = _role_management_handle
    save = lambda record: store.save_request("role_management", record, result)
    list_all = lambda: store.list_all("role_management")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'role_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'role_name': {'required': True}, 'display_name': {'required': False}, 'permissions': {'required': False}, 'access_level': {'required': False}, 'department': {'required': False}, 'is_active': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/role_management")
def role_management_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["role_management"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("role_management",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/role_management/{item_id}")
def role_management_get(item_id: int) -> Dict[str, Any]:
    record = store.get("role_management", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/role_management/{item_id}")
async def role_management_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "role_management", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "role_management", 'result': result}


@router.delete("/role_management/{item_id}")
async def role_management_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "role_management", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "role_management", 'result': result}


# --- clinic_analytics (kernel execute_action template) ---


def _clinic_analytics_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.clinic_analytics import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/clinic_analytics")
async def clinic_analytics_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("clinic_analytics", payload)
    CAPABILITY_ID = "clinic_analytics"
    handle = _clinic_analytics_handle
    save = lambda record: store.save_request("clinic_analytics", record, result)
    list_all = lambda: store.list_all("clinic_analytics")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'metric_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'metric_name': {'required': True}, 'metric_value': {'min': 0.0, 'max': 100000000.0, 'required': False}, 'period': {'required': False}, 'period_start': {'required': False}, 'period_end': {'required': False}, 'dimension': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/clinic_analytics")
def clinic_analytics_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["clinic_analytics"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("clinic_analytics",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/clinic_analytics/{item_id}")
def clinic_analytics_get(item_id: int) -> Dict[str, Any]:
    record = store.get("clinic_analytics", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/clinic_analytics/{item_id}")
async def clinic_analytics_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "clinic_analytics", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "clinic_analytics", 'result': result}


@router.delete("/clinic_analytics/{item_id}")
async def clinic_analytics_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "clinic_analytics", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "clinic_analytics", 'result': result}


@router.post("/work_queue")
async def work_queue_enqueue(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain(
        "enqueue", str((payload or {}).get("capability_id") or ""), payload or {}
    )
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'result': result}


@router.post("/work_queue/{item_id}/process")
async def work_queue_process(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("process", "", {"id": item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'result': result}


@router.get("/work_queue")
def work_queue_list() -> Dict[str, Any]:
    from app import work_queue as _work_queue
    return {"items": _work_queue.list_all()}

