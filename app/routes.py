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


# --- complaints_management (kernel execute_action template) ---


def _complaints_management_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.complaints_management import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/complaints_management")
async def complaints_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("complaints_management", payload)
    CAPABILITY_ID = "complaints_management"
    handle = _complaints_management_handle
    save = lambda record: store.save("complaints_management", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("complaints_management", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'school', 'category', 'priority', 'description', 'raised_by', 'raised_by_role']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'school': {'required': True}, 'site_code': {'required': False}, 'category': {'allowed_values': ['electrical', 'plumbing', 'hvac', 'cleaning', 'safety', 'grounds', 'furniture', 'it_av', 'pest_control', 'other'], 'required': True}, 'priority': {'allowed_values': ['critical', 'high', 'medium', 'low'], 'required': True}, 'description': {'required': True}, 'raised_by': {'required': True}, 'raised_by_role': {'allowed_values': ['school_staff', 'parent', 'management', 'student'], 'required': True}, 'contact_email': {'required': False}, 'contact_phone': {'required': False}, 'logged_by': {'required': False}, 'assigned_to': {'required': False}, 'assignment_mode': {'allowed_values': ['auto', 'manual', 'unassigned'], 'required': False}, 'reported_at': {'required': False}, 'due_at': {'required': False}, 'sla_hours': {'min': 1, 'max': 720, 'required': False}, 'closed_at': {'required': False}, 'resolution_notes': {'required': False}, 'work_order_reference': {'required': False}}
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


@router.get("/complaints_management")
def complaints_management_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["complaints_management"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("complaints_management", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/complaints_management/{item_id}")
def complaints_management_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("complaints_management", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/complaints_management/{item_id}")
async def complaints_management_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "complaints_management", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "complaints_management", 'result': result}


@router.delete("/complaints_management/{item_id}")
async def complaints_management_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "complaints_management", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "complaints_management", 'result': result}


# --- auto_assignment (kernel execute_action template) ---


def _auto_assignment_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.auto_assignment import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/auto_assignment")
async def auto_assignment_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("auto_assignment", payload)
    CAPABILITY_ID = "auto_assignment"
    handle = _auto_assignment_handle
    save = lambda record: store.save("auto_assignment", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("auto_assignment", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'complaint_reference', 'school', 'category', 'priority', 'required_trade', 'assignment_mode']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'complaint_reference': {'required': True}, 'school': {'required': True}, 'category': {'allowed_values': ['electrical', 'plumbing', 'hvac', 'cleaning', 'safety', 'grounds', 'furniture', 'it_av', 'pest_control', 'other'], 'required': True}, 'priority': {'allowed_values': ['critical', 'high', 'medium', 'low'], 'required': True}, 'required_trade': {'required': True}, 'required_skill': {'required': False}, 'candidate_count': {'min': 0, 'max': 500, 'required': False}, 'assigned_to': {'required': False}, 'assigned_role': {'allowed_values': ['technician', 'cleaner', 'supervisor'], 'required': False}, 'assignment_mode': {'allowed_values': ['auto', 'manual', 'unassigned'], 'required': True}, 'match_score': {'min': 0, 'max': 100, 'required': False}, 'workload_score': {'min': 0, 'max': 100, 'required': False}, 'queue_position': {'min': 0, 'max': 10000, 'required': False}, 'override_reason': {'required': False}, 'assigned_at': {'required': False}}
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


@router.get("/auto_assignment")
def auto_assignment_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["auto_assignment"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("auto_assignment", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/auto_assignment/{item_id}")
def auto_assignment_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("auto_assignment", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/auto_assignment/{item_id}")
async def auto_assignment_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "auto_assignment", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "auto_assignment", 'result': result}


@router.delete("/auto_assignment/{item_id}")
async def auto_assignment_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "auto_assignment", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "auto_assignment", 'result': result}


# --- workforce_management (kernel execute_action template) ---


def _workforce_management_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.workforce_management import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/workforce_management")
async def workforce_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("workforce_management", payload)
    CAPABILITY_ID = "workforce_management"
    handle = _workforce_management_handle
    save = lambda record: store.save("workforce_management", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("workforce_management", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'school', 'team_name', 'team_type', 'shift', 'headcount']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'school': {'required': True}, 'team_name': {'required': True}, 'team_type': {'allowed_values': ['technician', 'cleaner', 'supervisor', 'mixed'], 'required': True}, 'trade': {'required': False}, 'shift': {'allowed_values': ['morning', 'afternoon', 'night', 'split'], 'required': True}, 'headcount': {'min': 1, 'max': 500, 'required': True}, 'lead_name': {'required': False}, 'lead_email': {'required': False}, 'contact_phone': {'required': False}, 'active': {'required': False}, 'open_jobs': {'min': 0, 'max': 10000, 'required': False}, 'notes': {'required': False}}
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


@router.get("/workforce_management")
def workforce_management_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["workforce_management"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("workforce_management", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/workforce_management/{item_id}")
def workforce_management_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("workforce_management", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/workforce_management/{item_id}")
async def workforce_management_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "workforce_management", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "workforce_management", 'result': result}


@router.delete("/workforce_management/{item_id}")
async def workforce_management_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "workforce_management", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "workforce_management", 'result': result}


# --- management_dashboards (kernel execute_action template) ---


def _management_dashboards_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.management_dashboards import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/management_dashboards")
async def management_dashboards_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("management_dashboards", payload)
    CAPABILITY_ID = "management_dashboards"
    handle = _management_dashboards_handle
    save = lambda record: store.save("management_dashboards", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("management_dashboards", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'scope', 'school', 'period', 'complaints_open']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'scope': {'allowed_values': ['school', 'portfolio'], 'required': True}, 'school': {'required': True}, 'period': {'required': True}, 'complaints_open': {'min': 0, 'max': 100000, 'required': True}, 'complaints_in_progress': {'min': 0, 'max': 100000, 'required': False}, 'complaints_closed': {'min': 0, 'max': 100000, 'required': False}, 'jobs_in_progress': {'min': 0, 'max': 100000, 'required': False}, 'sla_breaches': {'min': 0, 'max': 100000, 'required': False}, 'sla_compliance_pct': {'min': 0, 'max': 100, 'required': False}, 'avg_closure_hours': {'min': 0, 'max': 10000, 'required': False}, 'headline': {'required': False}, 'generated_at': {'required': False}}
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


@router.get("/management_dashboards")
def management_dashboards_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["management_dashboards"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("management_dashboards", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/management_dashboards/{item_id}")
def management_dashboards_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("management_dashboards", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/management_dashboards/{item_id}")
async def management_dashboards_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "management_dashboards", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "management_dashboards", 'result': result}


@router.delete("/management_dashboards/{item_id}")
async def management_dashboards_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "management_dashboards", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "management_dashboards", 'result': result}


# --- reporting (kernel execute_action template) ---


def _reporting_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.reporting import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/reporting")
async def reporting_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("reporting", payload)
    CAPABILITY_ID = "reporting"
    handle = _reporting_handle
    save = lambda record: store.save("reporting", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("reporting", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'report_type', 'scope', 'school', 'period_start', 'period_end', 'complaints_total']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'report_type': {'allowed_values': ['daily', 'weekly', 'monthly', 'on_demand'], 'required': True}, 'scope': {'allowed_values': ['school', 'portfolio'], 'required': True}, 'school': {'required': True}, 'period_start': {'required': True}, 'period_end': {'required': True}, 'complaints_total': {'min': 0, 'max': 1000000, 'required': True}, 'closed_total': {'min': 0, 'max': 1000000, 'required': False}, 'avg_closure_hours': {'min': 0, 'max': 100000, 'required': False}, 'sla_compliance_pct': {'min': 0, 'max': 100, 'required': False}, 'top_category': {'required': False}, 'busiest_school': {'required': False}, 'recipients': {'required': False}, 'generated_at': {'required': False}}
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


@router.get("/reporting")
def reporting_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["reporting"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("reporting", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/reporting/{item_id}")
def reporting_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("reporting", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/reporting/{item_id}")
async def reporting_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "reporting", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "reporting", 'result': result}


@router.delete("/reporting/{item_id}")
async def reporting_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "reporting", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "reporting", 'result': result}


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
    required_fields = ['reference', 'status', 'principal', 'role', 'school', 'access_scope']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'principal': {'required': True}, 'principal_email': {'required': False}, 'role': {'allowed_values': ['management', 'admin', 'technician', 'cleaner', 'complainant', 'school_staff'], 'required': True}, 'school': {'required': True}, 'access_scope': {'allowed_values': ['portfolio', 'school', 'assigned_jobs', 'own_complaints'], 'required': True}, 'permissions': {'required': False}, 'granted_by': {'required': False}, 'effective_from': {'required': False}, 'last_review_at': {'required': False}, 'active': {'required': False}, 'notes': {'required': False}}
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


# --- erp_integration (kernel execute_action template) ---


def _erp_integration_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.erp_integration import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/erp_integration")
async def erp_integration_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("erp_integration", payload)
    CAPABILITY_ID = "erp_integration"
    handle = _erp_integration_handle
    save = lambda record: store.save("erp_integration", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("erp_integration", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'integration', 'mode', 'entity_type', 'direction']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'integration': {'allowed_values': ['erp'], 'required': True}, 'mode': {'allowed_values': ['placeholder'], 'required': True}, 'entity_type': {'allowed_values': ['purchase_order', 'invoice', 'vendor', 'staff_roster', 'asset'], 'required': True}, 'direction': {'allowed_values': ['inbound', 'outbound'], 'required': True}, 'external_reference': {'required': False}, 'endpoint': {'required': False}, 'currency': {'required': False}, 'amount': {'min': 0, 'max': 100000000, 'required': False}, 'sync_state': {'allowed_values': ['not_implemented', 'queued', 'blocked'], 'required': False}, 'last_sync_at': {'required': False}, 'detail': {'required': False}, 'notes': {'required': False}}
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


@router.get("/erp_integration")
def erp_integration_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["erp_integration"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("erp_integration", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/erp_integration/{item_id}")
def erp_integration_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("erp_integration", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/erp_integration/{item_id}")
async def erp_integration_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "erp_integration", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "erp_integration", 'result': result}


@router.delete("/erp_integration/{item_id}")
async def erp_integration_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "erp_integration", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "erp_integration", 'result': result}


# --- booking_system_integration (kernel execute_action template) ---


def _booking_system_integration_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.booking_system_integration import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/booking_system_integration")
async def booking_system_integration_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("booking_system_integration", payload)
    CAPABILITY_ID = "booking_system_integration"
    handle = _booking_system_integration_handle
    save = lambda record: store.save("booking_system_integration", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("booking_system_integration", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'integration', 'mode', 'booking_reference', 'school', 'facility', 'slot_start']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'integration': {'allowed_values': ['booking_system'], 'required': True}, 'mode': {'allowed_values': ['placeholder'], 'required': True}, 'booking_reference': {'required': True}, 'school': {'required': True}, 'facility': {'required': True}, 'slot_start': {'required': True}, 'slot_end': {'required': False}, 'requested_by': {'required': False}, 'sync_state': {'allowed_values': ['not_implemented', 'queued', 'blocked'], 'required': False}, 'last_sync_at': {'required': False}, 'detail': {'required': False}, 'notes': {'required': False}}
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


@router.get("/booking_system_integration")
def booking_system_integration_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["booking_system_integration"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("booking_system_integration", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/booking_system_integration/{item_id}")
def booking_system_integration_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("booking_system_integration", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/booking_system_integration/{item_id}")
async def booking_system_integration_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "booking_system_integration", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "booking_system_integration", 'result': result}


@router.delete("/booking_system_integration/{item_id}")
async def booking_system_integration_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "booking_system_integration", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "booking_system_integration", 'result': result}


@router.post("/work_queue")
async def work_queue_enqueue(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain(
        "enqueue", str((payload or {}).get("capability_id") or ""), payload or {},
        context=product_context(request),
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
    from app.kernel_bridge import product_context
    result = await perform_domain("process", "", {"id": item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'result': result}


@router.get("/work_queue")
def work_queue_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    from app import work_queue as _work_queue
    return {"items": _work_queue.list_all(tenant_id=tenant.tenant_id)}



# --- answer authority (precedence.v1) ---------------------------------
#
# An answer the console asks for carries the layer it came from, so an
# operator can see whose claim they are reading. The ladder is versioned
# data (app/authority.py), not prose in this route.
@router.get("/authority")
def answer_authority() -> Dict[str, Any]:
    from app import authority

    ladder = authority.ladder()
    return {
        "version": ladder["version"],
        "layers": ladder["layers"],
        "label": authority.label("formulas"),
        "sample": authority.winner(
            [
                {
                    "layer": "formulas",
                    "value": "sla_compliance_pct",
                    "score": 1.0,
                },
                {
                    "layer": "procedures",
                    "value": "review the rota",
                    "score": 0.5,
                },
            ]
        ),
        "note": (
            "the model is told which layer won; it never chooses. Money in "
            "this platform is AED, the currency the brief names for the "
            "Dubai schools estate."
        ),
    }
