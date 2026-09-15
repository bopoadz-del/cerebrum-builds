"""POST/GET /v1/{capability_id} — schema-sample accept and one-record persist."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.auth import require_operator
from app.block_inputs import record_mutation_audit
from app.dispatch import load_handler
from app.domain import matches_keyword
from app.jobs import JOBS, capabilities, catalog, gates, inventory, provenance
from app.schema import REQUIRED_CAPABILITY_IDS, SPECS, get_spec, validate_payload
from app.store import delete as store_delete
from app.store import get as store_get
from app.store import list_all

router = APIRouter()


@router.get("/v1/admin/export")
def admin_export(request: Request) -> Dict[str, Any]:
    principal = require_operator(request)
    return {
        "ok": True,
        "capabilities": list(REQUIRED_CAPABILITY_IDS),
        "principal": principal.as_dict(),
    }


@router.get("/v1/jobs")
def list_jobs() -> Dict[str, Any]:
    return {"ok": True, "jobs": JOBS}


@router.get("/v1/catalog")
def get_catalog() -> Dict[str, Any]:
    return catalog()


@router.get("/v1/inventory")
def get_inventory() -> Dict[str, Any]:
    return inventory()


@router.get("/v1/capabilities")
def get_capabilities() -> Dict[str, Any]:
    return capabilities()


@router.get("/v1/gates")
def get_gates() -> Dict[str, Any]:
    return gates()


@router.get("/v1/provenance")
def get_provenance() -> Dict[str, Any]:
    return provenance()


def _validated(capability_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    clean, error = validate_payload(capability_id, payload)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return clean or {}


@router.post("/v1/{capability_id}")
def post_capability(
    capability_id: str, request_payload: Dict[str, Any], request: Request
) -> Dict[str, Any]:
    principal = require_operator(request)
    if capability_id not in SPECS:
        raise HTTPException(status_code=404, detail="unknown capability")
    payload = _validated(capability_id, request_payload)
    claimed = request_payload.get("actor") or request_payload.get("user_id")
    payload = {
        **payload,
        "claimed_actor": claimed,
        "actor": principal.subject,
        "actor_role": principal.role,
        "user_id": principal.subject,
        "capability": capability_id,
    }
    handle = load_handler(capability_id)
    try:
        result = handle(payload)
    except Exception as exc:
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": str(exc), "capability": capability_id},
        )
    if not isinstance(result, dict):
        return {"ok": False, "error": "handler returned a non-object", "capability": capability_id}
    if result.get("ok") is False:
        return result
    record_mutation_audit(
        principal,
        action=f"mutate:{capability_id}",
        resource=str(payload.get("reference") or payload.get("title") or "sample"),
        details={
            "status": payload.get("status", "open"),
            "capability": capability_id,
            "title": payload.get("title") or payload.get("reference") or "sample",
            "category": "data_access",
        },
    )
    result.setdefault("ok", True)
    result.setdefault("capability", capability_id)
    result.setdefault("actor", principal.subject)
    result.setdefault("actor_role", principal.role)
    return result


@router.get("/v1/{capability_id}")
def get_capability(
    capability_id: str, q: Optional[str] = Query(default=None)
) -> Dict[str, Any]:
    if capability_id not in SPECS:
        raise HTTPException(status_code=404, detail="unknown capability")
    spec = get_spec(capability_id)
    records = list_all(spec["entity"])
    if q:
        records = [row for row in records if matches_keyword(row, q)]
    return {
        "ok": True,
        "capability": capability_id,
        "entity": spec["entity"],
        "records": records,
        "items": records,
        "count": len(records),
    }


@router.get("/v1/{capability_id}/{item_id}")
def get_capability_item(capability_id: str, item_id: str) -> Dict[str, Any]:
    if capability_id not in SPECS:
        raise HTTPException(status_code=404, detail="unknown capability")
    spec = get_spec(capability_id)
    record = store_get(spec["entity"], item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": capability_id, "record": record, **record}


@router.delete("/v1/{capability_id}/{item_id}")
def delete_capability_item(
    capability_id: str, item_id: str, request: Request
) -> Dict[str, Any]:
    principal = require_operator(request)
    if capability_id not in SPECS:
        raise HTTPException(status_code=404, detail="unknown capability")
    spec = get_spec(capability_id)
    existing = store_get(spec["entity"], item_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="not found")
    store_delete(spec["entity"], item_id)
    record_mutation_audit(
        principal,
        action=f"delete:{capability_id}",
        resource=str(existing.get("reference") or item_id),
        details={"status": existing.get("status", "closed"), "capability": capability_id},
    )
    return {"ok": True, "deleted": True, "id": existing.get("id"), "capability": capability_id}


@router.get("/v1")
def list_capabilities() -> Dict[str, Any]:
    return {
        "ok": True,
        "product": "Productivity Platform",
        "capabilities": list(REQUIRED_CAPABILITY_IDS),
    }
