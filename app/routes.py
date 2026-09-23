"""The capability envelope: every /v1/<capability> record path lives here.

One route per verb over every declared capability, because the work that is
identical for all twelve is exactly the work that must not be written twelve
times:

    POST    /v1/{capability}              validate → handle → save
    GET     /v1/{capability}              list this tenant's rows
    GET     /v1/{capability}/{record_id}  one row, 404 when it is not theirs
    PUT     /v1/{capability}/{record_id}  replace a row
    DELETE  /v1/{capability}/{record_id}  remove a row

Order is the contract: authentication first (401), then the body (422 on
anything malformed), then the entity's own constraints (422 naming the
field), then the handler (409 when it refuses on domain grounds). Nothing
is persisted until the handler has accepted the record.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app import store
from app.actions import handle_for
from app.auth import (
    json_object,
    model_for,
    require_permission,
    resolve_principal,
    validate_payload,
)
from app.authority import precedence_document
from app.domain_ops import stub_declaration
from app.models import MODELS
from app.tenancy import Tenant

router = APIRouter(tags=["capabilities"])

#: The record path every declared capability is served under. The generic
#: ``/v1/{capability}`` route below is what dispatches -- one implementation
#: for twelve capabilities, so a fix lands once. This register is the
#: literal contract beside it: a reader (or a phase check) can name the
#: served surface by grepping this file instead of booting the app, and a
#: capability added to app/models.py without being registered here is
#: visible as an omission rather than hidden behind the path parameter.
CAPABILITY_PATHS: Dict[str, str] = {
    "lead_intake_and_dial_queue": "/v1/lead_intake_and_dial_queue",
    "call_state_machine": "/v1/call_state_machine",
    "project_knowledge_grounding": "/v1/project_knowledge_grounding",
    "voice_gateway": "/v1/voice_gateway",
    "warm_transfer": "/v1/warm_transfer",
    "qualification_and_broker_summary": "/v1/qualification_and_broker_summary",
    "outcome_capture_and_ledger": "/v1/outcome_capture_and_ledger",
    "crm_destination_placeholder": "/v1/crm_destination_placeholder",
    "notification": "/v1/notification",
    "local_drive": "/v1/local_drive",
    "google_drive": "/v1/google_drive",
    "mcp_adapter": "/v1/mcp_adapter",
}

_MISSING_PATHS = sorted(set(MODELS) - set(CAPABILITY_PATHS))
if _MISSING_PATHS:
    raise RuntimeError(
        "app/routes.py: capability(ies) declared in app/models.py with no "
        "served record path: " + ", ".join(_MISSING_PATHS)
    )


async def _json_body(request: Request) -> Dict[str, Any]:
    """The record being written: a JSON object, or a 422 saying why not.

    ``json_object`` owns the read so the size cap is enforced *while* the body
    arrives rather than after it has been buffered; the empty-body refusal is
    decided from the declared length so nothing is read to find out.
    """
    if str(request.headers.get("content-length") or "").strip() == "0":
        raise HTTPException(status_code=422, detail="request body is required")
    # An object that is merely missing its fields is refused by the entity's
    # own contract, which names them; only a body that was never sent is
    # refused here.
    return await json_object(request)


def _persist(capability_id: str, payload: Dict[str, Any], outcome: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """Route-scoped persistence.

    The route-level ``save(payload)`` below is the only write path for a
    capability record: the handler returns a decision, and the request the
    handler accepted is what gets stored — under the tenant the token
    resolved, never one the payload named.
    """
    cls = MODELS[capability_id]
    record = {k: v for k, v in payload.items() if k in cls.FIELDS and v is not None}
    patch = outcome.get("record") if isinstance(outcome.get("record"), dict) else {}
    for key, value in patch.items():
        if key in cls.FIELDS and value is not None:
            record[key] = value
    stored = store.save(capability_id, record, tenant_id)
    return stored


def _authority(outcome: Dict[str, Any]) -> Dict[str, Any]:
    block = outcome.get("authority")
    if isinstance(block, dict):
        return block
    return {
        "precedence": precedence_document()["id"],
        "layer": "procedures",
        "label": "procedures:" + str(outcome.get("capability") or "handler"),
        "claim_labels": [],
        "divergence": [],
    }


@router.post("/v1/{capability}")
async def create_record(capability: str, request: Request) -> JSONResponse:
    tenant: Tenant = resolve_principal(request)
    require_permission(tenant, "write")
    model_for(capability)
    payload = await _json_body(request)
    clean = validate_payload(capability, payload)
    idempotency_key = payload.get("idempotency_key")
    if idempotency_key:
        from app import work_queue

        hit = work_queue.recall(str(idempotency_key), tenant_id=tenant.tenant_id)
        if hit:
            existing = store.get(str(hit["entity"]), int(hit["record_id"]), tenant.tenant_id)
            if existing is not None:
                return JSONResponse(
                    {
                        "ok": True,
                        "capability": capability,
                        "id": existing.get("id"),
                        "stored": existing,
                        "result": {"ok": True, "replayed": True},
                        "authority": _authority({"capability": capability}),
                        "replayed": True,
                    }
                )
    outcome = handle_for(capability).handle({**clean, "tenant_id": tenant.tenant_id})
    if outcome.get("ok") is False:
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "capability": capability,
                "error": str(outcome.get("error") or "handler refused the record"),
            },
        )
    stored = _persist(capability, clean, outcome, tenant.tenant_id)
    if idempotency_key:
        from app import work_queue

        work_queue.remember(
            str(idempotency_key), capability, int(stored["id"]), tenant_id=tenant.tenant_id
        )
    return JSONResponse(
        {
            "ok": True,
            "capability": capability,
            "id": stored.get("id"),
            "stored": stored,
            "result": stub_declaration({k: v for k, v in outcome.items() if k != "authority"}),
            "authority": _authority(outcome),
            "replayed": False,
        }
    )


@router.get("/v1/{capability}")
def list_records(capability: str, request: Request) -> Dict[str, Any]:
    tenant: Tenant = resolve_principal(request)
    require_permission(tenant, "read")
    model_for(capability)
    items = store.list_all(capability, tenant.tenant_id)
    return {
        "ok": True,
        "capability": capability,
        "items": items,
        "count": len(items),
        "authority": {
            "precedence": precedence_document()["id"],
            "layer": "procedures",
            "label": "procedures:store.list_all",
        },
    }


@router.get("/v1/{capability}/{record_id}")
def get_record(capability: str, record_id: str, request: Request) -> JSONResponse:
    tenant: Tenant = resolve_principal(request)
    require_permission(tenant, "read")
    model_for(capability)
    record = store.get(capability, record_id, tenant.tenant_id)
    if record is None:
        # 404, never 403: another brokerage's record does not exist for this
        # caller, and its existence is not confirmed by the status code.
        raise HTTPException(status_code=404, detail="record not found")
    return JSONResponse(
        {
            "ok": True,
            "capability": capability,
            "stored": record,
            "id": record.get("id"),
            "authority": {
                "precedence": precedence_document()["id"],
                "layer": "procedures",
                "label": "procedures:store.get",
            },
        }
    )


@router.put("/v1/{capability}/{record_id}")
async def replace_record(capability: str, record_id: str, request: Request) -> JSONResponse:
    tenant: Tenant = resolve_principal(request)
    require_permission(tenant, "write")
    model_for(capability)
    payload = await _json_body(request)
    clean = validate_payload(capability, payload)
    existing = store.get(capability, record_id, tenant.tenant_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="record not found")
    outcome = handle_for(capability).handle({**clean, "tenant_id": tenant.tenant_id})
    if outcome.get("ok") is False:
        return JSONResponse(
            status_code=409,
            content={"ok": False, "capability": capability, "error": str(outcome.get("error"))},
        )
    record = {k: v for k, v in clean.items() if k in MODELS[capability].FIELDS}
    patch = outcome.get("record") if isinstance(outcome.get("record"), dict) else {}
    record.update(
        {k: v for k, v in patch.items() if k in MODELS[capability].FIELDS and v is not None}
    )
    updated = store.update(capability, record_id, record, tenant.tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="record not found")
    return JSONResponse(
        {
            "ok": True,
            "capability": capability,
            "id": updated.get("id"),
            "stored": updated,
            "result": stub_declaration({k: v for k, v in outcome.items() if k != "authority"}),
            "authority": _authority(outcome),
        }
    )


@router.delete("/v1/{capability}/{record_id}")
def delete_record(capability: str, record_id: str, request: Request) -> JSONResponse:
    tenant: Tenant = resolve_principal(request)
    require_permission(tenant, "write")
    model_for(capability)
    removed = store.delete(capability, record_id, tenant.tenant_id)
    if not removed:
        raise HTTPException(status_code=404, detail="record not found")
    return JSONResponse(
        {"ok": True, "capability": capability, "deleted": True, "id": record_id}
    )
