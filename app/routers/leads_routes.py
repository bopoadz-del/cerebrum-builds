"""Lead intake from a file, and the dial queue that follows from it.

    POST /v1/leads/import            a brokerage CSV / Excel export in
    GET  /v1/dial-queue              the paced dial list for a campaign
    POST /v1/dial-queue/{id}/claim   take one item, tenant-scoped
    POST /v1/dial-queue/{id}/process run it through its capability

The list is durable: an item is a row, so a restart mid-campaign loses no
queued call, and the daily cap and concurrency are policy settings on the
queue rather than numbers baked into a loop.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app import dispatch, domain, store, work_queue
from app.actions import handle_for
from app.auth import int_query, json_object, optional_int, require_permission, resolve_principal
from app.models import MODELS
from app.tenancy import Tenant

router = APIRouter(tags=["leads"])


@router.post("/v1/leads/import")
async def import_leads(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """Parse a brokerage lead file into dial-list rows for this tenant."""
    require_permission(tenant, "write")
    body = await json_object(request)
    text = body.get("text") or body.get("content") or ""
    if not str(text).strip():
        raise HTTPException(status_code=422, detail="Missing required field: text")
    campaign = str(body.get("campaign") or "")
    project_tag = str(body.get("project_tag") or "")
    language = str(body.get("language") or "en")[:2]
    try:
        parsed = dispatch.execute("capture", "parse", {"text": str(text)})
    except dispatch.BlockRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    queued: List[Dict[str, Any]] = []
    refused: List[Dict[str, Any]] = []
    for lead in parsed["leads"]:
        record = {
            "lead_name": lead.get("lead_name"),
            "phone": lead.get("phone"),
            "project_tag": lead.get("project_tag") or project_tag,
            "language": (lead.get("language") or language)[:2].lower(),
            "campaign": lead.get("campaign") or campaign,
            "source_file": body.get("file_name") or "upload",
            "reference": f"{campaign or 'intake'}:row{lead.get('source_row')}",
            "status": "open",
        }
        for optional in ("lead_email", "property_type", "area", "timeline", "notes"):
            if lead.get(optional):
                record[optional] = lead[optional]
        if record["language"] not in ("en", "ar"):
            record["language"] = "en"
        outcome = handle_for("lead_intake_and_dial_queue").handle(
            {**record, "tenant_id": tenant.tenant_id}
        )
        if outcome.get("ok") is False:
            refused.append({"row": lead.get("source_row"), "error": outcome.get("error")})
            continue
        patch = outcome.get("record") or {}
        stored = store.save(
            "lead_intake_and_dial_queue",
            {**{k: v for k, v in record.items() if k in MODELS["lead_intake_and_dial_queue"].FIELDS},
             **{k: v for k, v in patch.items() if k in MODELS["lead_intake_and_dial_queue"].FIELDS and v is not None}},
            tenant.tenant_id,
        )
        item = work_queue.enqueue(
            "lead_intake_and_dial_queue",
            {"lead_id": stored["id"], "call_sid": None, "campaign": record["campaign"]},
            tenant_id=tenant.tenant_id,
        ) if stored.get("dialable") else None
        queued.append(
            {
                "id": stored["id"],
                "lead_name": stored.get("lead_name"),
                "language": stored.get("language"),
                "queue_state": stored.get("queue_state"),
                "dialable": bool(stored.get("dialable")),
                "reason": stored.get("dialable_reason"),
                "queue_item": (item or {}).get("id"),
            }
        )
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "campaign": campaign or None,
        "file_rows": parsed["parsed"] + len(parsed["rejected"]),
        "columns": parsed["columns"],
        "accepted": len(queued),
        "refused": refused + parsed["rejected"],
        "queued": queued,
        "queue_depth": work_queue.depth(tenant_id=tenant.tenant_id),
        "authority": parsed.get("authority"),
    }


@router.get("/v1/leads/import")
def import_register(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """What each lead file has become, per source file.

    The read twin of the import: an operator who has uploaded three sheets
    needs to see which file produced which leads, how many of them are
    dialable, and what held the rest — without re-uploading anything. An
    empty register is a valid answer (200, zero batches); the ledger of
    nothing is not a missing resource.
    """
    require_permission(tenant, "read")
    campaign = request.query_params.get("campaign")
    rows = store.list_all("lead_intake_and_dial_queue", tenant.tenant_id)
    if campaign:
        rows = [row for row in rows if str(row.get("campaign") or "") == campaign]
    batches: Dict[str, Dict[str, Any]] = {}
    held_reasons: Dict[str, int] = {}
    for row in rows:
        key = str(row.get("source_file") or "upload")
        batch = batches.setdefault(
            key,
            {
                "source_file": key,
                "leads": 0,
                "dialable": 0,
                "held": 0,
                "languages": {},
                "projects": [],
                "campaigns": [],
            },
        )
        batch["leads"] += 1
        if row.get("dialable"):
            batch["dialable"] += 1
        else:
            batch["held"] += 1
            reason = str(row.get("dialable_reason") or "undialable")
            held_reasons[reason] = held_reasons.get(reason, 0) + 1
        language = str(row.get("language") or "en")
        batch["languages"][language] = batch["languages"].get(language, 0) + 1
        project = str(row.get("project_tag") or "")
        if project and project not in batch["projects"]:
            batch["projects"].append(project)
        campaign_name = str(row.get("campaign") or "")
        if campaign_name and campaign_name not in batch["campaigns"]:
            batch["campaigns"].append(campaign_name)
    register = [
        {**batch, "projects": sorted(batch["projects"]), "campaigns": sorted(batch["campaigns"])}
        for batch in sorted(batches.values(), key=lambda item: item["source_file"])
    ]
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "campaign": campaign or None,
        "batches": register,
        "source_files": [item["source_file"] for item in register],
        "lead_count": len(rows),
        "dialable": sum(item["dialable"] for item in register),
        "held": held_reasons,
        "queue_depth": work_queue.depth(tenant_id=tenant.tenant_id),
        "authority": {
            "precedence": "precedence.v1",
            "layer": "procedures",
            "label": "procedures:leads.import_register",
            "claim_labels": [],
            "divergence": [],
        },
    }


@router.get("/v1/dial-queue")
def dial_queue(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    campaign = request.query_params.get("campaign")
    attempted = int_query(request, "attempted_today", 0, minimum=0, maximum=100_000)
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "depth": work_queue.depth(tenant_id=tenant.tenant_id),
        **domain.dial_queue(
            tenant.tenant_id,
            campaign=campaign,
            attempted_today=attempted,
        ),
    }


@router.post("/v1/dial-queue/{item_id}/claim")
def claim(item_id: int, request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "process")
    item = work_queue.claim_pending(item_id, tenant_id=tenant.tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="queue item is not pending for this tenant")
    return {"ok": True, "item": item}


@router.post("/v1/dial-queue/{item_id}/process")
def process(item_id: int, request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """Run a claimed item through its capability, as the item's own tenant."""
    require_permission(tenant, "process")
    claimed = work_queue.claim_pending(item_id, tenant_id=tenant.tenant_id)
    if claimed is None:
        existing = work_queue.get(item_id, tenant_id=tenant.tenant_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="queue item not found")
        raise HTTPException(status_code=409, detail="queue item is not pending")
    item_tenant = str(claimed.get("tenant_id") or "")
    if not item_tenant:
        raise HTTPException(status_code=409, detail="queue item carries no tenant")
    payload = dict(claimed.get("payload") or {})
    capability_id = str(claimed.get("capability_id") or "")
    lead_id = payload.get("lead_id")
    lead: Optional[Dict[str, Any]] = None
    if lead_id and capability_id in MODELS:
        lead = store.get("lead_intake_and_dial_queue", lead_id, item_tenant)
    record = {
        "call_sid": payload.get("call_sid") or f"pending-{item_id}",
        "to_number": (lead or {}).get("phone_e164") or (lead or {}).get("phone") or "",
        "action": "originate",
        "language": (lead or {}).get("language") or "en",
        "reference": (lead or {}).get("reference") or f"queue-{item_id}",
        "status": "open",
        "tenant_id": item_tenant,
    }
    if not record["to_number"]:
        outcome: Dict[str, Any] = {
            "ok": False,
            "error": "queued lead has no dialable number",
        }
    else:
        outcome = handle_for("voice_gateway").handle(record)
    status = work_queue.PROCESSED if outcome.get("ok") is not False else work_queue.FAILED
    marked = work_queue.mark(
        item_id,
        status,
        {"capability": capability_id, "decision": outcome.get("decision"), "error": outcome.get("error")},
        from_status=work_queue.PROCESSING,
        tenant_id=tenant.tenant_id,
    )
    if marked is None or marked.get("status") in (work_queue.PENDING, work_queue.PROCESSING):
        raise HTTPException(status_code=409, detail="queue item was not processed")
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "item": marked,
        "result": outcome,
        "lead": lead,
    }
