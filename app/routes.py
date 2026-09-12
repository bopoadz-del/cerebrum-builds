"""POST/GET /v1/{capability_id} — schema-sample accept and one-record persist."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.dispatch import load_handler
from app.schema import RESERVED_FIELDS, REQUIRED_CAPABILITY_IDS, SPECS, STATUS_VALUES, get_spec
from app.store import list_all, save as store_save

router = APIRouter()


@router.get("/v1/admin/export")
def admin_export(request: Request) -> Dict[str, Any]:
    token = request.headers.get("authorization") or request.headers.get("x-api-token")
    if not token:
        raise HTTPException(status_code=401, detail="token required")
    return {"ok": True, "capabilities": list(REQUIRED_CAPABILITY_IDS)}


def _validate_payload(capability_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    spec = get_spec(capability_id)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be an object")
    reserved = RESERVED_FIELDS.intersection(payload)
    if reserved:
        raise HTTPException(
            status_code=422, detail=f"reserved-keyword fields refused: {sorted(reserved)}"
        )
    fields = spec["FIELDS"]
    constraints = spec["CONSTRAINTS"]
    missing = [name for name in ("reference", "status") if name not in payload]
    if missing:
        raise HTTPException(status_code=422, detail=f"missing required field: {missing[0]}")
    status = payload.get("status")
    allowed = (constraints.get("status") or {}).get("allowed_values") or list(STATUS_VALUES)
    if status not in allowed:
        raise HTTPException(status_code=422, detail=f"status must be one of {allowed}")
    for name, meta in fields.items():
        if name in payload and meta.get("type") == "string" and payload[name] is None:
            raise HTTPException(status_code=422, detail=f"{name} must be a string")
    return payload


@router.post("/v1/{capability_id}")
def post_capability(capability_id: str, request_payload: Dict[str, Any]) -> Dict[str, Any]:
    if capability_id not in SPECS:
        raise HTTPException(status_code=404, detail="unknown capability")
    payload = _validate_payload(capability_id, request_payload)
    spec = get_spec(capability_id)
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
    store_save(spec["entity"], payload)
    result.setdefault("ok", True)
    result.setdefault("capability", capability_id)
    return result


@router.get("/v1/{capability_id}")
def get_capability(capability_id: str) -> Dict[str, Any]:
    if capability_id not in SPECS:
        raise HTTPException(status_code=404, detail="unknown capability")
    spec = get_spec(capability_id)
    records = list_all(spec["entity"])
    return {
        "ok": True,
        "capability": capability_id,
        "entity": spec["entity"],
        "records": records,
        "count": len(records),
    }


@router.get("/v1")
def list_capabilities() -> Dict[str, Any]:
    return {
        "ok": True,
        "product": "Cerebrum Steward",
        "capabilities": list(REQUIRED_CAPABILITY_IDS),
    }
