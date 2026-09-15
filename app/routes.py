"""POST/GET /v1/{capability_id} — schema-sample accept and one-record persist."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.auth import require_operator
from app.block_inputs import record_mutation_audit
from app.dispatch import load_handler
from app.domain import search_notes
from app.jobs import JOBS, catalog, gates, inventory, provenance
from app.schema import (
    RESERVED_FIELDS,
    REQUIRED_CAPABILITY_IDS,
    SPECS,
    STATUS_VALUES,
    get_spec,
    schema_sample,
)
from app.store import delete as store_delete
from app.store import get as store_get
from app.store import list_all

router = APIRouter()


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
def list_capability_items() -> Dict[str, Any]:
    return {
        "ok": True,
        "items": [
            {
                "id": spec["id"],
                "entity": spec["entity"],
                "block_ids": list(spec["BLOCK_IDS"]),
            }
            for spec in SPECS.values()
        ],
    }


@router.get("/v1/gates")
def get_gates() -> Dict[str, Any]:
    return gates()


@router.get("/v1/provenance")
def get_provenance() -> Dict[str, Any]:
    return provenance()


@router.get("/v1/admin/export")
def admin_export(request: Request) -> Dict[str, Any]:
    principal = require_operator(request)
    return {
        "ok": True,
        "capabilities": list(REQUIRED_CAPABILITY_IDS),
        "principal": principal.as_dict(),
    }


def _validate_payload(capability_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    spec = get_spec(capability_id)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be an object")
    reserved = RESERVED_FIELDS.intersection(payload)
    if reserved:
        raise HTTPException(
            status_code=422, detail=f"reserved-keyword fields refused: {sorted(reserved)}"
        )
    if not payload:
        return schema_sample(capability_id)
    fields = spec["FIELDS"]
    constraints = spec["CONSTRAINTS"]
    missing = [name for name in ("reference", "status") if name not in payload]
    if missing:
        raise HTTPException(status_code=422, detail=f"missing required field: {missing[0]}")
    status = payload.get("status")
    allowed = (constraints.get("status") or {}).get("allowed_values") or list(STATUS_VALUES)
    if status not in allowed:
        raise HTTPException(status_code=422, detail=f"status must be one of {allowed}")
    for name, meta in constraints.items():
        if name == "status" or name not in payload:
            continue
        allowed_values = meta.get("allowed_values")
        if allowed_values and payload[name] not in allowed_values:
            raise HTTPException(status_code=422, detail=f"{name} must be one of {allowed_values}")
    for name, meta in fields.items():
        if name in payload and meta.get("type") == "string" and payload[name] is None:
            raise HTTPException(status_code=422, detail=f"{name} must be a string")
    return payload


@router.post("/v1/{capability_id}")
def post_capability(
    capability_id: str, request_payload: Dict[str, Any], request: Request
) -> Dict[str, Any]:
    principal = require_operator(request)
    if capability_id not in SPECS:
        raise HTTPException(status_code=404, detail="unknown capability")
    payload = _validate_payload(capability_id, request_payload)
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
        resource=str(payload.get("reference") or "sample"),
        details={
            "status": payload.get("status", "open"),
            "capability": capability_id,
            "title": payload.get("title") or payload.get("reference") or "sample",
            "category": "productivity",
        },
    )
    result.setdefault("ok", True)
    result.setdefault("capability", capability_id)
    result.setdefault("actor", principal.subject)
    result.setdefault("actor_role", principal.role)
    return result


@router.get("/v1/{capability_id}/{item_id}")
def get_capability_item(capability_id: str, item_id: str) -> Dict[str, Any]:
    if capability_id not in SPECS:
        raise HTTPException(status_code=404, detail="unknown capability")
    spec = get_spec(capability_id)
    record = store_get(spec["entity"], item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "ok": True,
        "capability": capability_id,
        "entity": spec["entity"],
        "record": record,
        "item": record,
    }


@router.delete("/v1/{capability_id}/{item_id}")
def delete_capability_item(capability_id: str, item_id: str, request: Request) -> Dict[str, Any]:
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
    return {
        "ok": True,
        "capability": capability_id,
        "deleted": True,
        "id": existing.get("id"),
        "actor": principal.subject,
    }


@router.get("/v1/{capability_id}")
def get_capability(
    capability_id: str, q: Optional[str] = Query(default=None)
) -> Dict[str, Any]:
    if capability_id not in SPECS:
        raise HTTPException(status_code=404, detail="unknown capability")
    spec = get_spec(capability_id)
    records = list_all(spec["entity"])
    if q:
        records = search_notes(records, q)
    return {
        "ok": True,
        "capability": capability_id,
        "entity": spec["entity"],
        "records": records,
        "items": records,
        "count": len(records),
        "query": q,
    }


@router.get("/v1")
def list_capabilities() -> Dict[str, Any]:
    return {
        "ok": True,
        "product": "Productivity Platform",
        "capabilities": list(REQUIRED_CAPABILITY_IDS),
    }
