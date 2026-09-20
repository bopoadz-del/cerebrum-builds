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

# --- job_and_site_tracking (factory kernel execute_action template) ---


def _job_and_site_tracking_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.job_and_site_tracking import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/job_and_site_tracking")
async def job_and_site_tracking_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("job_and_site_tracking", payload)
    CAPABILITY_ID = "job_and_site_tracking"
    handle = _job_and_site_tracking_handle
    save = lambda record: store.save("job_and_site_tracking", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("job_and_site_tracking", tenant_id=tenant.tenant_id)
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


@router.get("/job_and_site_tracking")
def job_and_site_tracking_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["job_and_site_tracking"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("job_and_site_tracking", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"), order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)), offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/job_and_site_tracking/{item_id}")
def job_and_site_tracking_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("job_and_site_tracking", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/job_and_site_tracking/{item_id}")
async def job_and_site_tracking_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "job_and_site_tracking", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "job_and_site_tracking", 'result': result}


@router.delete("/job_and_site_tracking/{item_id}")
async def job_and_site_tracking_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "job_and_site_tracking", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "job_and_site_tracking", 'result': result}


# --- commercials_and_valuations (factory kernel execute_action template) ---


def _commercials_and_valuations_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.commercials_and_valuations import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/commercials_and_valuations")
async def commercials_and_valuations_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("commercials_and_valuations", payload)
    CAPABILITY_ID = "commercials_and_valuations"
    handle = _commercials_and_valuations_handle
    save = lambda record: store.save("commercials_and_valuations", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("commercials_and_valuations", tenant_id=tenant.tenant_id)
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


@router.get("/commercials_and_valuations")
def commercials_and_valuations_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["commercials_and_valuations"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("commercials_and_valuations", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"), order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)), offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/commercials_and_valuations/{item_id}")
def commercials_and_valuations_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("commercials_and_valuations", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/commercials_and_valuations/{item_id}")
async def commercials_and_valuations_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "commercials_and_valuations", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "commercials_and_valuations", 'result': result}


@router.delete("/commercials_and_valuations/{item_id}")
async def commercials_and_valuations_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "commercials_and_valuations", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "commercials_and_valuations", 'result': result}


# --- document_qa_and_indexing (factory kernel execute_action template) ---


def _document_qa_and_indexing_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.document_qa_and_indexing import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/document_qa_and_indexing")
async def document_qa_and_indexing_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("document_qa_and_indexing", payload)
    CAPABILITY_ID = "document_qa_and_indexing"
    handle = _document_qa_and_indexing_handle
    save = lambda record: store.save("document_qa_and_indexing", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("document_qa_and_indexing", tenant_id=tenant.tenant_id)
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


@router.get("/document_qa_and_indexing")
def document_qa_and_indexing_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["document_qa_and_indexing"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("document_qa_and_indexing", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"), order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)), offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/document_qa_and_indexing/{item_id}")
def document_qa_and_indexing_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("document_qa_and_indexing", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/document_qa_and_indexing/{item_id}")
async def document_qa_and_indexing_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "document_qa_and_indexing", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "document_qa_and_indexing", 'result': result}


@router.delete("/document_qa_and_indexing/{item_id}")
async def document_qa_and_indexing_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "document_qa_and_indexing", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "document_qa_and_indexing", 'result': result}


# --- safety_and_compliance (factory kernel execute_action template) ---


def _safety_and_compliance_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.safety_and_compliance import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/safety_and_compliance")
async def safety_and_compliance_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("safety_and_compliance", payload)
    CAPABILITY_ID = "safety_and_compliance"
    handle = _safety_and_compliance_handle
    save = lambda record: store.save("safety_and_compliance", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("safety_and_compliance", tenant_id=tenant.tenant_id)
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


@router.get("/safety_and_compliance")
def safety_and_compliance_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["safety_and_compliance"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("safety_and_compliance", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"), order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)), offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/safety_and_compliance/{item_id}")
def safety_and_compliance_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("safety_and_compliance", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/safety_and_compliance/{item_id}")
async def safety_and_compliance_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "safety_and_compliance", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "safety_and_compliance", 'result': result}


@router.delete("/safety_and_compliance/{item_id}")
async def safety_and_compliance_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "safety_and_compliance", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "safety_and_compliance", 'result': result}


# --- progress_cost_dashboard (factory kernel execute_action template) ---


def _progress_cost_dashboard_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.progress_cost_dashboard import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/progress_cost_dashboard")
async def progress_cost_dashboard_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("progress_cost_dashboard", payload)
    CAPABILITY_ID = "progress_cost_dashboard"
    handle = _progress_cost_dashboard_handle
    save = lambda record: store.save("progress_cost_dashboard", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("progress_cost_dashboard", tenant_id=tenant.tenant_id)
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


@router.get("/progress_cost_dashboard")
def progress_cost_dashboard_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["progress_cost_dashboard"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("progress_cost_dashboard", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"), order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)), offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/progress_cost_dashboard/{item_id}")
def progress_cost_dashboard_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("progress_cost_dashboard", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/progress_cost_dashboard/{item_id}")
async def progress_cost_dashboard_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "progress_cost_dashboard", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "progress_cost_dashboard", 'result': result}


@router.delete("/progress_cost_dashboard/{item_id}")
async def progress_cost_dashboard_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "progress_cost_dashboard", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "progress_cost_dashboard", 'result': result}


# --- automation_reminders_escalation (factory kernel execute_action template) ---


def _automation_reminders_escalation_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.automation_reminders_escalation import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/automation_reminders_escalation")
async def automation_reminders_escalation_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("automation_reminders_escalation", payload)
    CAPABILITY_ID = "automation_reminders_escalation"
    handle = _automation_reminders_escalation_handle
    save = lambda record: store.save("automation_reminders_escalation", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("automation_reminders_escalation", tenant_id=tenant.tenant_id)
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


@router.get("/automation_reminders_escalation")
def automation_reminders_escalation_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["automation_reminders_escalation"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("automation_reminders_escalation", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"), order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)), offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/automation_reminders_escalation/{item_id}")
def automation_reminders_escalation_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("automation_reminders_escalation", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/automation_reminders_escalation/{item_id}")
async def automation_reminders_escalation_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "automation_reminders_escalation", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "automation_reminders_escalation", 'result': result}


@router.delete("/automation_reminders_escalation/{item_id}")
async def automation_reminders_escalation_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "automation_reminders_escalation", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "automation_reminders_escalation", 'result': result}


# --- audit_and_access_control (factory kernel execute_action template) ---


def _audit_and_access_control_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.audit_and_access_control import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/audit_and_access_control")
async def audit_and_access_control_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("audit_and_access_control", payload)
    CAPABILITY_ID = "audit_and_access_control"
    handle = _audit_and_access_control_handle
    save = lambda record: store.save("audit_and_access_control", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("audit_and_access_control", tenant_id=tenant.tenant_id)
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


@router.get("/audit_and_access_control")
def audit_and_access_control_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["audit_and_access_control"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("audit_and_access_control", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"), order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)), offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/audit_and_access_control/{item_id}")
def audit_and_access_control_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("audit_and_access_control", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/audit_and_access_control/{item_id}")
async def audit_and_access_control_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "audit_and_access_control", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "audit_and_access_control", 'result': result}


@router.delete("/audit_and_access_control/{item_id}")
async def audit_and_access_control_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "audit_and_access_control", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "audit_and_access_control", 'result': result}


# --- team_notifications (factory kernel execute_action template) ---


def _team_notifications_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.team_notifications import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/team_notifications")
async def team_notifications_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("team_notifications", payload)
    CAPABILITY_ID = "team_notifications"
    handle = _team_notifications_handle
    save = lambda record: store.save("team_notifications", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("team_notifications", tenant_id=tenant.tenant_id)
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


@router.get("/team_notifications")
def team_notifications_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["team_notifications"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("team_notifications", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"), order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)), offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/team_notifications/{item_id}")
def team_notifications_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("team_notifications", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/team_notifications/{item_id}")
async def team_notifications_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "team_notifications", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "team_notifications", 'result': result}


@router.delete("/team_notifications/{item_id}")
async def team_notifications_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "team_notifications", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "team_notifications", 'result': result}


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


