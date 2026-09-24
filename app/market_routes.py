"""Authenticated operator routes for property-market evidence.

These are deliberately not capabilities: they persist nothing and stay off the
cite-or-refuse path. Brokers pull official sold / asking context here so
pitches do not invent market numbers. Fail-closed auth via
``require_platform_token`` (same principal path as capability writes).
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request

from app.connectors import apify_bayut, dld, dxb_data, market_status

router = APIRouter(prefix="/market", tags=["market"])


def _payload(body: Any) -> Dict[str, Any]:
    return dict(body or {}) if isinstance(body, dict) else {}


@router.get("/status")
def market_sources_status(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    require_platform_token(request)
    return {"ok": True, **market_status()}


@router.post("/dxb/snapshot")
async def dxb_snapshot(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    require_platform_token(request)
    data = _payload(payload)
    return dxb_data.area_snapshot(
        data.get("area"),
        property_type=str(data.get("property_type") or "Flat"),
    )


@router.post("/dxb/yield")
async def dxb_yield(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    require_platform_token(request)
    data = _payload(payload)
    return dxb_data.rental_yield(
        data.get("area"),
        property_type=str(data.get("property_type") or "Flat"),
    )


@router.post("/dxb/compare")
async def dxb_compare(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    require_platform_token(request)
    data = _payload(payload)
    return dxb_data.compare_areas(
        data.get("areas") or [],
        property_type=str(data.get("property_type") or "Flat"),
    )


@router.post("/dld/sales_stats")
async def dld_sales_stats(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    require_platform_token(request)
    data = _payload(payload)
    return dld.sales_stats(
        data.get("area"),
        property_type=str(data.get("property_type") or "all"),
        bedrooms=str(data.get("bedrooms") or "all"),
        date_from=str(data.get("date_from") or ""),
        date_to=str(data.get("date_to") or ""),
    )


@router.post("/apify/bayut_buy")
async def apify_bayut_buy(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    require_platform_token(request)
    data = _payload(payload)
    return apify_bayut.harvest_buy(
        start_urls=data.get("startUrls") or data.get("start_urls"),
        max_items=data.get("maxItems") or data.get("max_items") or apify_bayut.DEFAULT_MAX_ITEMS,
        wait_secs=data.get("waitSecs") or data.get("wait_secs") or apify_bayut.DEFAULT_WAIT_SECS,
        full_details=bool(data.get("fullDetails") or data.get("full_details") or False),
    )
