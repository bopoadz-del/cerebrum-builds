"""Platform surfaces: authority, connectors, settings, blocks and MCP.

    GET  /v1/auth/whoami        the tenant this token resolves to
    GET  /v1/authority          precedence.v1 as data
    GET  /v1/connectors         every connector's real state
    GET  /v1/settings           which operator settings are set (never values)
    GET  /v1/blocks             the blocks this platform composes
    POST /v1/connectors/webhook/probe  one real outbound round trip
    POST /v1/mcp                MCP JSON-RPC over the same capabilities

``/v1/auth/*`` is rate limited by the observability middleware; the rest are
tenant scoped and answer 401 without a token like every other route.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request

from app import config, dispatch, domain
from app.auth import int_query, json_object, optional_int, require_permission, resolve_principal
from app.authority import precedence_document
from app.tenancy import Tenant
from app.tenancy import single_tenant_posture
from app.voice import twilio_client

router = APIRouter(tags=["platform"])


@router.get("/v1/auth/whoami")
def whoami(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    return {"ok": True, "tenant": tenant.to_dict(), "product": config.PRODUCT_NAME}


@router.get("/v1/authority")
def authority(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    document = precedence_document()
    return {
        "ok": True,
        "precedence": document,
        "authority": {
            "precedence": document["id"],
            "layer": "procedures",
            "label": "procedures:precedence.v1",
        },
    }


@router.get("/v1/connectors")
def connectors(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """What is connected, what is stubbed, and what each one is missing."""
    require_permission(tenant, "read")
    edge = twilio_client().state()
    rows: List[Dict[str, Any]] = [
        {
            "connector": "twilio_programmable_voice",
            "connected": edge["connected"],
            "mode": "live" if edge["live"] else "stubbed",
            "blocks_unavailable": edge["unavailable_blocks"],
            "note": "outbound calling edge; ships stubbed until an account and caller number are connected",
        },
        {
            "connector": "sales_channel_webhook",
            "connected": bool(config.BROKER_ALERT_WEBHOOK),
            "mode": "live" if config.BROKER_ALERT_WEBHOOK else "stubbed",
            "blocks_unavailable": [] if config.BROKER_ALERT_WEBHOOK else ["SALES_CHANNEL_WEBHOOK"],
            "note": "the platform's one live outbound delivery",
        },
        {
            "connector": "crm_destination",
            "connected": bool(config.CRM_DESTINATION),
            "mode": "placeholder",
            "blocks_unavailable": [] if config.CRM_DESTINATION else ["CRM_DESTINATION"],
            "note": "the brief names no CRM: a shaped record is all this produces",
        },
        {
            "connector": "google_drive",
            "connected": bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET and config.GOOGLE_REFRESH_TOKEN),
            "mode": "stubbed",
            "blocks_unavailable": [
                name
                for name, value in (
                    ("GOOGLE_CLIENT_ID", config.GOOGLE_CLIENT_ID),
                    ("GOOGLE_CLIENT_SECRET", config.GOOGLE_CLIENT_SECRET),
                    ("GOOGLE_REFRESH_TOKEN", config.GOOGLE_REFRESH_TOKEN),
                    ("GOOGLE_DRIVE_FOLDER_ID", config.GOOGLE_DRIVE_FOLDER_ID),
                )
                if not value
            ],
            "note": "request shape is built and certified against a fake transport; no call is made",
        },
        {
            "connector": "llm_provider",
            "connected": bool(config.LLM_PROVIDER and config.LLM_API_KEY),
            "mode": "model" if config.LLM_PROVIDER and config.LLM_API_KEY else "deterministic",
            "blocks_unavailable": []
            if config.LLM_PROVIDER and config.LLM_API_KEY
            else ["LLM_PROVIDER", "LLM_API_KEY"],
            "note": "without a provider the dialogue runs a deterministic grounded planner",
        },
    ]
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "connectors": rows,
        "stubbed": [row["connector"] for row in rows if row["mode"] in ("stubbed", "placeholder", "deterministic")],
        "authority": {"precedence": "precedence.v1", "layer": "procedures", "label": "procedures:connector-state"},
    }


@router.get("/v1/settings")
def settings(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """Which settings are set — never their values, and never a default invented."""
    require_permission(tenant, "read")
    names = (
        "CURRENCY",
        "VAT_RATE",
        "BROKER_COMMISSION_RATE",
        "DEFAULT_COUNTRY_CODE",
        "DAILY_CALL_CAP",
        "CONCURRENCY",
        "MAX_ATTEMPTS",
        "RETRY_BACKOFF_MINUTES",
        "CALL_WINDOW_EN",
        "CALL_WINDOW_AR",
        "CALL_WINDOW_TZ",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_CALLER_NUMBER",
        "BROKER_TRANSFER_NUMBER",
        "SALES_CHANNEL_WEBHOOK",
        "CRM_DESTINATION",
        "LOCAL_DRIVE_ROOT",
        "LLM_PROVIDER",
        "LLM_API_KEY",
    )
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "settings": [
            {"name": name, "set": bool(config.env(name)), "required_by_brief": name in config.UNSET_BY_BRIEF}
            for name in names
        ],
        "money": config.money_settings_state(),
        "read_posture": {
            "single_tenant": single_tenant_posture(),
            "anonymous_reads": (
                "resolve to this deployment's own tenant"
                if single_tenant_posture()
                else "refused with 401: a second tenant exists, so a read needs a principal"
            ),
            "switch": (
                "bind PLATFORM_TOKEN_B or TENANT_TOKENS to require a token on reads; "
                "writes always require one"
            ),
        },
        "note": "values are never returned; an unset money setting makes the pricing formulas refuse by name",
        "authority": {
            "precedence": "precedence.v1",
            "layer": "procedures",
            "label": "procedures:app.config",
            "claim_labels": [],
            "divergence": [],
        },
    }


@router.get("/v1/blocks")
def blocks(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    catalog = dispatch.catalog()
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "blocks": catalog,
        "count": len(catalog),
        "authority": {"precedence": "precedence.v1", "layer": "procedures", "label": "procedures:dispatch.catalog"},
    }


@router.post("/v1/connectors/webhook/probe")
async def webhook_probe(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """Prove the live connector: one real POST to the operator's webhook.

    The URL is checked against the private-address guard before anything is
    dialled, so this cannot be turned into a request-forgery probe against
    the operator's own network.
    """
    require_permission(tenant, "write")
    body = await json_object(request)
    url = str((body or {}).get("url") or config.BROKER_ALERT_WEBHOOK or "")
    if not url:
        raise HTTPException(status_code=422, detail="Missing required field: url")
    result = dispatch.execute(
        "webhook",
        "probe",
        {"url": url, "payload": {"event": "callops.probe", "tenant": tenant.tenant_id}},
    )
    if result.get("delivery") == "refused":
        raise HTTPException(status_code=422, detail=str(result.get("error")))
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "delivery": result.get("delivery"),
        "response_code": int(result.get("response_code") or 0),
        "url": result.get("url"),
        "authority": {"precedence": "precedence.v1", "layer": "procedures", "label": "procedures:webhook"},
    }


@router.post("/v1/mcp")
async def mcp(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """MCP JSON-RPC over the declared capabilities, as this tenant.

    Listing the tools is a read. ``tools/call`` runs a capability handler and
    persists through the same envelope the HTTP route uses, so it asks for
    the write permission — the surface is not a way around the permission
    model the routes enforce.
    """
    body = await json_object(request)
    method = str(body.get("method") or "")
    require_permission(tenant, "write" if method == "tools/call" else "read")
    params = dict(body.get("params") or {})
    if not method:
        raise HTTPException(status_code=422, detail="Missing required field: method")
    from app.actions import handle_for

    outcome = handle_for("mcp_adapter").handle(
        {
            "method": method,
            "tool": params.get("name") or params.get("tool"),
            "arguments": params.get("arguments"),
            "tenant_id": tenant.tenant_id,
            "reference": f"mcp:{method}",
            "status": "open",
        }
    )
    if outcome.get("ok") is False:
        return {"ok": False, "jsonrpc": {"jsonrpc": "2.0", "error": {"code": -32600, "message": outcome.get("error")}}}
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "jsonrpc": outcome.get("jsonrpc"),
        "result": outcome.get("record"),
        "authority": {
            "precedence": "precedence.v1",
            "layer": "procedures",
            "label": "procedures:mcp_adapter",
            "claim_labels": [],
            "divergence": [],
        },
    }
