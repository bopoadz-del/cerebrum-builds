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


# --- patient_records (factory kernel execute_action template) ---


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
    tenant = require_platform_token(request)
    reject_invalid_payload("patient_records", payload)
    CAPABILITY_ID = "patient_records"
    handle = _patient_records_handle
    save = lambda record: store.save("patient_records", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("patient_records", tenant_id=tenant.tenant_id)
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


@router.get("/patient_records")
def patient_records_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
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
        return store.query("patient_records", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/patient_records/{item_id}")
def patient_records_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("patient_records", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/patient_records/{item_id}")
async def patient_records_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "patient_records", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_records", 'result': result}


@router.delete("/patient_records/{item_id}")
async def patient_records_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "patient_records", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "patient_records", 'result': result}


# --- appointment_scheduling (factory kernel execute_action template) ---


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
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
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
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
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


# --- treatment_records (factory kernel execute_action template) ---


def _treatment_records_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.treatment_records import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/treatment_records")
async def treatment_records_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("treatment_records", payload)
    CAPABILITY_ID = "treatment_records"
    handle = _treatment_records_handle
    save = lambda record: store.save("treatment_records", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("treatment_records", tenant_id=tenant.tenant_id)
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


@router.get("/treatment_records")
def treatment_records_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["treatment_records"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("treatment_records", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/treatment_records/{item_id}")
def treatment_records_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("treatment_records", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/treatment_records/{item_id}")
async def treatment_records_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "treatment_records", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "treatment_records", 'result': result}


@router.delete("/treatment_records/{item_id}")
async def treatment_records_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "treatment_records", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "treatment_records", 'result': result}


# --- invoicing (factory kernel execute_action template) ---


def _invoicing_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.invoicing import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/invoicing")
async def invoicing_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("invoicing", payload)
    CAPABILITY_ID = "invoicing"
    handle = _invoicing_handle
    save = lambda record: store.save("invoicing", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("invoicing", tenant_id=tenant.tenant_id)
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


@router.get("/invoicing")
def invoicing_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["invoicing"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("invoicing", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/invoicing/{item_id}")
def invoicing_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("invoicing", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/invoicing/{item_id}")
async def invoicing_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "invoicing", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "invoicing", 'result': result}


@router.delete("/invoicing/{item_id}")
async def invoicing_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "invoicing", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "invoicing", 'result': result}


# --- recall_reminders (factory kernel execute_action template) ---


def _recall_reminders_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.recall_reminders import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/recall_reminders")
async def recall_reminders_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("recall_reminders", payload)
    CAPABILITY_ID = "recall_reminders"
    handle = _recall_reminders_handle
    save = lambda record: store.save("recall_reminders", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("recall_reminders", tenant_id=tenant.tenant_id)
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


@router.get("/recall_reminders")
def recall_reminders_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["recall_reminders"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("recall_reminders", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/recall_reminders/{item_id}")
def recall_reminders_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("recall_reminders", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/recall_reminders/{item_id}")
async def recall_reminders_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "recall_reminders", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "recall_reminders", 'result': result}


@router.delete("/recall_reminders/{item_id}")
async def recall_reminders_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "recall_reminders", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "recall_reminders", 'result': result}


# --- staff_roles_permissions (factory kernel execute_action template) ---


def _staff_roles_permissions_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.staff_roles_permissions import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/staff_roles_permissions")
async def staff_roles_permissions_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("staff_roles_permissions", payload)
    CAPABILITY_ID = "staff_roles_permissions"
    handle = _staff_roles_permissions_handle
    save = lambda record: store.save("staff_roles_permissions", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("staff_roles_permissions", tenant_id=tenant.tenant_id)
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


@router.get("/staff_roles_permissions")
def staff_roles_permissions_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["staff_roles_permissions"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("staff_roles_permissions", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/staff_roles_permissions/{item_id}")
def staff_roles_permissions_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("staff_roles_permissions", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/staff_roles_permissions/{item_id}")
async def staff_roles_permissions_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "staff_roles_permissions", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "staff_roles_permissions", 'result': result}


@router.delete("/staff_roles_permissions/{item_id}")
async def staff_roles_permissions_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "staff_roles_permissions", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "staff_roles_permissions", 'result': result}


# --- clinic_dashboard (factory kernel execute_action template) ---


def _clinic_dashboard_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.clinic_dashboard import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/clinic_dashboard")
async def clinic_dashboard_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("clinic_dashboard", payload)
    CAPABILITY_ID = "clinic_dashboard"
    handle = _clinic_dashboard_handle
    save = lambda record: store.save("clinic_dashboard", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("clinic_dashboard", tenant_id=tenant.tenant_id)
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


@router.get("/clinic_dashboard")
def clinic_dashboard_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["clinic_dashboard"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("clinic_dashboard", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/clinic_dashboard/{item_id}")
def clinic_dashboard_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("clinic_dashboard", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/clinic_dashboard/{item_id}")
async def clinic_dashboard_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "clinic_dashboard", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "clinic_dashboard", 'result': result}


@router.delete("/clinic_dashboard/{item_id}")
async def clinic_dashboard_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "clinic_dashboard", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "clinic_dashboard", 'result': result}


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

