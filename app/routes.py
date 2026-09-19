"""HTTP surface for the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

Capability routes run entirely in-process: the handler dispatches to the
vendored block and the ROUTE persists the request with the tenant resolved from
the authenticated principal (never from the body). No outbound call, no store
callback.

* ``POST /v1/{capability}`` — token-guarded. The record is completed from the
  capability's own schema when the body names no declared field, then validated
  against that schema (422 on a missing required field, an out-of-vocabulary
  ``status``, a broken bound, or a reserved keyword) and only then handed to
  ``handle()``. The record is written only when the handler reports success, so
  a failed block never persists a row.
* ``GET /v1/{capability}`` — the chain display board: readable without a token
  (the factory's PRODUCT round-trip reads it anonymously); a token that IS sent
  must be valid and its tenant scopes the read.

Scope
-----
READS  the request, the capability model, ``STORAGE_PATH``.
WRITES the request record to the capability's own entity.
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app import jobs, store
from app.auth import (
    prepare_create_payload,
    require_platform_token,
)
from app.tenancy import read_tenant

router = APIRouter()


@router.get("/jobs")
def list_jobs() -> Dict[str, Any]:
    """Roster of every kernel job description."""
    return {"jobs": jobs.JOBS}


@router.get("/catalog")
def catalog() -> Dict[str, Any]:
    """COLLECTOR - Binding surveyor."""
    return jobs.CATALOG


@router.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    """WRITER - Platform manufacturer. Capability HTTP surface."""
    return {"items": jobs.CAPABILITIES}


@router.get("/inventory")
def inventory() -> Dict[str, Any]:
    """CLONER - Block stocker. Read the pinned vendor lock live."""
    return jobs.inventory()


@router.get("/gates")
def gates() -> Dict[str, Any]:
    """TESTER - Acceptance inspector. Coverage only; does not run tests."""
    return jobs.GATES


@router.get("/provenance")
def provenance() -> Dict[str, Any]:
    """STORE_MANAGER - Store registrar. Clone register and provenance."""
    return jobs.provenance()


def _saver(capability_id: str, tenant: str):
    """The route's tenant-scoped writer: ``save(payload)`` writes the request."""

    def save(payload: Dict[str, Any]) -> Dict[str, Any]:
        return store.save(capability_id, payload, tenant_id=tenant)

    return save


def _run_handler(capability_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call the capability handler. A block refusal is data, not HTTP 500."""
    from app.actions import handler_for

    try:
        result = handler_for(capability_id)(payload)
    except Exception as exc:  # the block runtime refused; report, never 500
        return {"ok": False, "capability": capability_id,
                "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "capability": capability_id,
                "error": f"handle() returned {type(result).__name__}"}
    return result


# --- stock_inventory_management ---


@router.post("/stock_inventory_management")
async def stock_inventory_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Create one stock_inventory_management record, then persist it for the request's tenant."""
    principal = require_platform_token(request)
    record = prepare_create_payload("stock_inventory_management", payload)
    save = _saver("stock_inventory_management", principal.tenant)
    result = _run_handler("stock_inventory_management", record)
    if result.get("ok") is False:
        return {"ok": False, "capability": "stock_inventory_management",
                "error": result.get("error"), "results": result.get("results")}
    saved = save(record)
    return {"ok": True, "capability": "stock_inventory_management", "record": saved,
            "result": result.get("results", {})}


@router.get("/stock_inventory_management")
def stock_inventory_management_list(request: Request) -> Dict[str, Any]:
    """List persisted stock_inventory_management records for the caller's tenant."""
    tenant = read_tenant(request)
    rows = store.list_all("stock_inventory_management", tenant_id=tenant)
    return {"capability": "stock_inventory_management", "items": rows, "total": len(rows)}


@router.get("/stock_inventory_management/{record_id}")
def stock_inventory_management_read(record_id: int, request: Request) -> Dict[str, Any]:
    """Read one persisted stock_inventory_management record."""
    tenant = read_tenant(request)
    row = store.get("stock_inventory_management", record_id, tenant_id=tenant)
    if row is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"capability": "stock_inventory_management", "record": row}


# --- product_pricing ---


@router.post("/product_pricing")
async def product_pricing_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Create one product_pricing record, then persist it for the request's tenant."""
    principal = require_platform_token(request)
    record = prepare_create_payload("product_pricing", payload)
    save = _saver("product_pricing", principal.tenant)
    result = _run_handler("product_pricing", record)
    if result.get("ok") is False:
        return {"ok": False, "capability": "product_pricing",
                "error": result.get("error"), "results": result.get("results")}
    saved = save(record)
    return {"ok": True, "capability": "product_pricing", "record": saved,
            "result": result.get("results", {})}


@router.get("/product_pricing")
def product_pricing_list(request: Request) -> Dict[str, Any]:
    """List persisted product_pricing records for the caller's tenant."""
    tenant = read_tenant(request)
    rows = store.list_all("product_pricing", tenant_id=tenant)
    return {"capability": "product_pricing", "items": rows, "total": len(rows)}


@router.get("/product_pricing/{record_id}")
def product_pricing_read(record_id: int, request: Request) -> Dict[str, Any]:
    """Read one persisted product_pricing record."""
    tenant = read_tenant(request)
    row = store.get("product_pricing", record_id, tenant_id=tenant)
    if row is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"capability": "product_pricing", "record": row}


# --- delivery_dispatch_tracking ---


@router.post("/delivery_dispatch_tracking")
async def delivery_dispatch_tracking_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Create one delivery_dispatch_tracking record, then persist it for the request's tenant."""
    principal = require_platform_token(request)
    record = prepare_create_payload("delivery_dispatch_tracking", payload)
    save = _saver("delivery_dispatch_tracking", principal.tenant)
    result = _run_handler("delivery_dispatch_tracking", record)
    if result.get("ok") is False:
        return {"ok": False, "capability": "delivery_dispatch_tracking",
                "error": result.get("error"), "results": result.get("results")}
    saved = save(record)
    return {"ok": True, "capability": "delivery_dispatch_tracking", "record": saved,
            "result": result.get("results", {})}


@router.get("/delivery_dispatch_tracking")
def delivery_dispatch_tracking_list(request: Request) -> Dict[str, Any]:
    """List persisted delivery_dispatch_tracking records for the caller's tenant."""
    tenant = read_tenant(request)
    rows = store.list_all("delivery_dispatch_tracking", tenant_id=tenant)
    return {"capability": "delivery_dispatch_tracking", "items": rows, "total": len(rows)}


@router.get("/delivery_dispatch_tracking/{record_id}")
def delivery_dispatch_tracking_read(record_id: int, request: Request) -> Dict[str, Any]:
    """Read one persisted delivery_dispatch_tracking record."""
    tenant = read_tenant(request)
    row = store.get("delivery_dispatch_tracking", record_id, tenant_id=tenant)
    if row is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"capability": "delivery_dispatch_tracking", "record": row}


# --- fleet_cost_tracking ---


@router.post("/fleet_cost_tracking")
async def fleet_cost_tracking_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Create one fleet_cost_tracking record, then persist it for the request's tenant."""
    principal = require_platform_token(request)
    record = prepare_create_payload("fleet_cost_tracking", payload)
    save = _saver("fleet_cost_tracking", principal.tenant)
    result = _run_handler("fleet_cost_tracking", record)
    if result.get("ok") is False:
        return {"ok": False, "capability": "fleet_cost_tracking",
                "error": result.get("error"), "results": result.get("results")}
    saved = save(record)
    return {"ok": True, "capability": "fleet_cost_tracking", "record": saved,
            "result": result.get("results", {})}


@router.get("/fleet_cost_tracking")
def fleet_cost_tracking_list(request: Request) -> Dict[str, Any]:
    """List persisted fleet_cost_tracking records for the caller's tenant."""
    tenant = read_tenant(request)
    rows = store.list_all("fleet_cost_tracking", tenant_id=tenant)
    return {"capability": "fleet_cost_tracking", "items": rows, "total": len(rows)}


@router.get("/fleet_cost_tracking/{record_id}")
def fleet_cost_tracking_read(record_id: int, request: Request) -> Dict[str, Any]:
    """Read one persisted fleet_cost_tracking record."""
    tenant = read_tenant(request)
    row = store.get("fleet_cost_tracking", record_id, tenant_id=tenant)
    if row is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"capability": "fleet_cost_tracking", "record": row}


# --- management_reporting_dashboard ---


@router.post("/management_reporting_dashboard")
async def management_reporting_dashboard_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Create one management_reporting_dashboard record, then persist it for the request's tenant."""
    principal = require_platform_token(request)
    record = prepare_create_payload("management_reporting_dashboard", payload)
    save = _saver("management_reporting_dashboard", principal.tenant)
    result = _run_handler("management_reporting_dashboard", record)
    if result.get("ok") is False:
        return {"ok": False, "capability": "management_reporting_dashboard",
                "error": result.get("error"), "results": result.get("results")}
    saved = save(record)
    return {"ok": True, "capability": "management_reporting_dashboard", "record": saved,
            "result": result.get("results", {})}


@router.get("/management_reporting_dashboard")
def management_reporting_dashboard_list(request: Request) -> Dict[str, Any]:
    """List persisted management_reporting_dashboard records for the caller's tenant."""
    tenant = read_tenant(request)
    rows = store.list_all("management_reporting_dashboard", tenant_id=tenant)
    return {"capability": "management_reporting_dashboard", "items": rows, "total": len(rows)}


@router.get("/management_reporting_dashboard/{record_id}")
def management_reporting_dashboard_read(record_id: int, request: Request) -> Dict[str, Any]:
    """Read one persisted management_reporting_dashboard record."""
    tenant = read_tenant(request)
    row = store.get("management_reporting_dashboard", record_id, tenant_id=tenant)
    if row is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"capability": "management_reporting_dashboard", "record": row}


# --- user_roles_workforce ---


@router.post("/user_roles_workforce")
async def user_roles_workforce_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Create one user_roles_workforce record, then persist it for the request's tenant."""
    principal = require_platform_token(request)
    record = prepare_create_payload("user_roles_workforce", payload)
    save = _saver("user_roles_workforce", principal.tenant)
    result = _run_handler("user_roles_workforce", record)
    if result.get("ok") is False:
        return {"ok": False, "capability": "user_roles_workforce",
                "error": result.get("error"), "results": result.get("results")}
    saved = save(record)
    return {"ok": True, "capability": "user_roles_workforce", "record": saved,
            "result": result.get("results", {})}


@router.get("/user_roles_workforce")
def user_roles_workforce_list(request: Request) -> Dict[str, Any]:
    """List persisted user_roles_workforce records for the caller's tenant."""
    tenant = read_tenant(request)
    rows = store.list_all("user_roles_workforce", tenant_id=tenant)
    return {"capability": "user_roles_workforce", "items": rows, "total": len(rows)}


@router.get("/user_roles_workforce/{record_id}")
def user_roles_workforce_read(record_id: int, request: Request) -> Dict[str, Any]:
    """Read one persisted user_roles_workforce record."""
    tenant = read_tenant(request)
    row = store.get("user_roles_workforce", record_id, tenant_id=tenant)
    if row is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"capability": "user_roles_workforce", "record": row}


# --- document_knowledge_qa ---


@router.post("/document_knowledge_qa")
async def document_knowledge_qa_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Create one document_knowledge_qa record, then persist it for the request's tenant."""
    principal = require_platform_token(request)
    record = prepare_create_payload("document_knowledge_qa", payload)
    save = _saver("document_knowledge_qa", principal.tenant)
    result = _run_handler("document_knowledge_qa", record)
    if result.get("ok") is False:
        return {"ok": False, "capability": "document_knowledge_qa",
                "error": result.get("error"), "results": result.get("results")}
    saved = save(record)
    return {"ok": True, "capability": "document_knowledge_qa", "record": saved,
            "result": result.get("results", {})}


@router.get("/document_knowledge_qa")
def document_knowledge_qa_list(request: Request) -> Dict[str, Any]:
    """List persisted document_knowledge_qa records for the caller's tenant."""
    tenant = read_tenant(request)
    rows = store.list_all("document_knowledge_qa", tenant_id=tenant)
    return {"capability": "document_knowledge_qa", "items": rows, "total": len(rows)}


@router.get("/document_knowledge_qa/{record_id}")
def document_knowledge_qa_read(record_id: int, request: Request) -> Dict[str, Any]:
    """Read one persisted document_knowledge_qa record."""
    tenant = read_tenant(request)
    row = store.get("document_knowledge_qa", record_id, tenant_id=tenant)
    if row is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"capability": "document_knowledge_qa", "record": row}


# --- procedures_readiness_and_audit_trail ---


@router.post("/procedures_readiness_and_audit_trail")
async def procedures_readiness_and_audit_trail_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Create one procedures_readiness_and_audit_trail record, then persist it for the request's tenant."""
    principal = require_platform_token(request)
    record = prepare_create_payload("procedures_readiness_and_audit_trail", payload)
    save = _saver("procedures_readiness_and_audit_trail", principal.tenant)
    result = _run_handler("procedures_readiness_and_audit_trail", record)
    if result.get("ok") is False:
        return {"ok": False, "capability": "procedures_readiness_and_audit_trail",
                "error": result.get("error"), "results": result.get("results")}
    saved = save(record)
    return {"ok": True, "capability": "procedures_readiness_and_audit_trail", "record": saved,
            "result": result.get("results", {})}


@router.get("/procedures_readiness_and_audit_trail")
def procedures_readiness_and_audit_trail_list(request: Request) -> Dict[str, Any]:
    """List persisted procedures_readiness_and_audit_trail records for the caller's tenant."""
    tenant = read_tenant(request)
    rows = store.list_all("procedures_readiness_and_audit_trail", tenant_id=tenant)
    return {"capability": "procedures_readiness_and_audit_trail", "items": rows, "total": len(rows)}


@router.get("/procedures_readiness_and_audit_trail/{record_id}")
def procedures_readiness_and_audit_trail_read(record_id: int, request: Request) -> Dict[str, Any]:
    """Read one persisted procedures_readiness_and_audit_trail record."""
    tenant = read_tenant(request)
    row = store.get("procedures_readiness_and_audit_trail", record_id, tenant_id=tenant)
    if row is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"capability": "procedures_readiness_and_audit_trail", "record": row}

