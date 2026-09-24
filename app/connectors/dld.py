"""DLD property-data connector (dld-mcp data plane).

``dld-mcp`` (``uvx --with 'mcp<2' dld-mcp``) exposes ``query_dld`` over MCP
stdio and forwards to ``https://offerbrief.com/api/query``. CallOps talks to
that same HTTP data plane when ``DLD_QUERY_URL`` is set (typically
``https://offerbrief.com/api``). Pin ``mcp<2`` when running the MCP server —
FastMCP import fails on mcp 2.x.

Without ``DLD_QUERY_URL`` the connector answers ``status: not_configured`` and
never fabricates sold/rent stats.
"""

from __future__ import annotations

import os
from typing import Any, Dict
from urllib.parse import urljoin

from app.connectors._http import json_request
from app.security import InputRefused, clean_text

SOURCE_ID = "dld"
ENV_URL = "DLD_QUERY_URL"
DEFAULT_URL = "https://offerbrief.com/api"
MCP_COMMAND_DOCS = "uvx --with 'mcp<2' dld-mcp"

ALLOWED_TYPES = ("sales", "rentals")
ALLOWED_PROPERTY_TYPES = ("all", "apartment", "villa", "townhouse")
ALLOWED_BEDROOMS = ("all", "studio", "1", "2", "3", "4", "5+")
ALLOWED_METRICS = ("stats", "count", "list")


def configured() -> bool:
    return bool((os.environ.get(ENV_URL) or "").strip())


def query_base() -> str:
    return (os.environ.get(ENV_URL) or "").strip().rstrip("/")


def status() -> Dict[str, Any]:
    if not configured():
        return {
            "source": SOURCE_ID,
            "status": "not_configured",
            "env": ENV_URL,
            "mcp_command": MCP_COMMAND_DOCS,
            "error": (
                f"set {ENV_URL} (e.g. {DEFAULT_URL}) to enable DLD sales/rent "
                f"queries; MCP operators can also run `{MCP_COMMAND_DOCS}`"
            ),
        }
    return {
        "source": SOURCE_ID,
        "status": "configured",
        "env": ENV_URL,
        "url": query_base(),
        "mcp_command": MCP_COMMAND_DOCS,
    }


def _not_configured() -> Dict[str, Any]:
    body = status()
    body["ok"] = False
    return body


def query_dld(
    area: Any,
    *,
    type: str = "sales",
    property_type: str = "all",
    bedrooms: str = "all",
    date_from: str = "",
    date_to: str = "",
    metric: str = "stats",
    limit: int = 10,
) -> Dict[str, Any]:
    """Mirror of dld-mcp ``query_dld`` against the HTTP data plane."""
    if not configured():
        return _not_configured()
    try:
        area_text = clean_text(area, field="area", limit=120)
        if len(area_text) < 2:
            raise InputRefused("area must be at least 2 characters")
        kind = clean_text(type, field="type", limit=20).lower() or "sales"
        ptype = clean_text(property_type, field="property_type", limit=40).lower() or "all"
        beds = clean_text(bedrooms, field="bedrooms", limit=20).lower() or "all"
        metric_name = clean_text(metric, field="metric", limit=20).lower() or "stats"
        from_date = clean_text(date_from, field="date_from", limit=32)
        to_date = clean_text(date_to, field="date_to", limit=32)
    except InputRefused as exc:
        return {"ok": False, "source": SOURCE_ID, "status": "error", "error": str(exc)}

    if kind not in ALLOWED_TYPES:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": "type must be one of: " + ", ".join(ALLOWED_TYPES),
        }
    if ptype not in ALLOWED_PROPERTY_TYPES:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": "property_type must be one of: " + ", ".join(ALLOWED_PROPERTY_TYPES),
        }
    if beds not in ALLOWED_BEDROOMS:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": "bedrooms must be one of: " + ", ".join(ALLOWED_BEDROOMS),
        }
    if metric_name not in ALLOWED_METRICS:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": "metric must be one of: " + ", ".join(ALLOWED_METRICS),
        }

    try:
        capped = int(limit)
    except (TypeError, ValueError):
        return {"ok": False, "source": SOURCE_ID, "status": "error", "error": "limit must be an integer"}
    capped = max(1, min(capped, 50))

    params: Dict[str, Any] = {
        "area": area_text,
        "type": kind,
        "property_type": ptype,
        "bedrooms": beds,
        "metric": metric_name,
        "limit": capped,
    }
    if from_date:
        params["date_from"] = from_date
    if to_date:
        params["date_to"] = to_date

    endpoint = urljoin(query_base() + "/", "query")
    try:
        http_status, body, _headers = json_request(endpoint, method="GET", query=params, timeout=30.0)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }

    if http_status >= 400 and http_status != 404:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "http_status": http_status,
            "error": f"dld query HTTP {http_status}",
            "detail": body if isinstance(body, (dict, list, str)) else None,
        }
    if isinstance(body, dict) and body.get("error") and http_status >= 400:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "http_status": http_status,
            "error": str(body.get("error"))[:300],
            "detail": body,
        }
    return {
        "ok": True,
        "source": SOURCE_ID,
        "status": "ok",
        "tool": "query_dld",
        "params": params,
        "data": body,
    }


def sales_stats(
    area: Any,
    *,
    property_type: str = "all",
    bedrooms: str = "all",
    date_from: str = "",
    date_to: str = "",
) -> Dict[str, Any]:
    """Operator shorthand: DLD sales with ``metric=stats``."""
    return query_dld(
        area,
        type="sales",
        property_type=property_type,
        bedrooms=bedrooms,
        date_from=date_from,
        date_to=date_to,
        metric="stats",
        limit=10,
    )
