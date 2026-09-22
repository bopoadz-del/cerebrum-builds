"""DXB Data MCP connector — official DLD area medians and yields.

Source: ``https://dxbdata.io/mcp`` (JSON-RPC / MCP tools). Set
``DXB_DATA_MCP_URL`` to enable. Without it the connector answers
``status: not_configured`` and never fabricates market numbers.

Official area names are DLD English labels. Broker shorthand for JBR /
Dubai Marina often resolves to DLD area ``Marsa Dubai``; this client applies
that alias explicitly and reports it on the response.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Sequence

from app.connectors._http import json_request
from app.security import InputRefused, clean_text

SOURCE_ID = "dxb_data"
ENV_URL = "DXB_DATA_MCP_URL"
DEFAULT_URL = "https://dxbdata.io/mcp"

#: Broker shorthand → official DLD English area as served by DXB Data.
AREA_ALIASES = {
    "jbr": "Marsa Dubai",
    "jumeirah beach residence": "Marsa Dubai",
    "jumeirah beach residences": "Marsa Dubai",
    "dubai marina": "Marsa Dubai",
    "marina": "Marsa Dubai",
    "the marina": "Marsa Dubai",
}


def configured() -> bool:
    return bool((os.environ.get(ENV_URL) or "").strip())


def mcp_url() -> str:
    return (os.environ.get(ENV_URL) or "").strip()


def status() -> Dict[str, Any]:
    if not configured():
        return {
            "source": SOURCE_ID,
            "status": "not_configured",
            "env": ENV_URL,
            "error": f"set {ENV_URL} (e.g. {DEFAULT_URL}) to enable official DLD area medians/yields",
        }
    return {"source": SOURCE_ID, "status": "configured", "env": ENV_URL, "url": mcp_url()}


def resolve_area(area: Any) -> Dict[str, str]:
    """Return ``{requested, resolved, alias_applied}`` for a DXB area label."""
    requested = clean_text(area, field="area", limit=120)
    if not requested:
        raise InputRefused("area is required")
    key = requested.casefold().strip()
    resolved = AREA_ALIASES.get(key)
    if resolved:
        return {"requested": requested, "resolved": resolved, "alias_applied": key}
    return {"requested": requested, "resolved": requested, "alias_applied": ""}


def _not_configured() -> Dict[str, Any]:
    body = status()
    body["ok"] = False
    return body


def _rpc(method: str, params: Optional[Dict[str, Any]] = None, *, rpc_id: int = 1) -> Dict[str, Any]:
    url = mcp_url()
    if not url:
        return _not_configured()
    payload = {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params or {}}
    try:
        http_status, body, _headers = json_request(
            url,
            method="POST",
            body=payload,
            headers={"Accept": "application/json, text/event-stream"},
            timeout=30.0,
        )
    except Exception as exc:  # noqa: BLE001 - name the transport failure
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }
    if http_status >= 400:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "http_status": http_status,
            "error": f"dxb_data MCP HTTP {http_status}",
            "detail": body if isinstance(body, (dict, list, str)) else None,
        }
    if not isinstance(body, dict):
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": "dxb_data MCP returned a non-object body",
        }
    if body.get("error"):
        err = body["error"]
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": str(err.get("message") if isinstance(err, dict) else err)[:300],
            "detail": err,
        }
    return {"ok": True, "source": SOURCE_ID, "status": "ok", "rpc": body}


def _unwrap_tool_result(rpc_body: Dict[str, Any]) -> Any:
    result = (rpc_body.get("rpc") or {}).get("result")
    if not isinstance(result, dict):
        return result
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and first.get("type") == "text":
            text = first.get("text")
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except ValueError:
                    return text
    return result.get("structuredContent") or result


def call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not configured():
        return _not_configured()
    tool = clean_text(name, field="tool", limit=80)
    if not tool:
        return {"ok": False, "source": SOURCE_ID, "status": "error", "error": "tool name is required"}
    rpc = _rpc("tools/call", {"name": tool, "arguments": dict(arguments or {})})
    if not rpc.get("ok"):
        return rpc
    data = _unwrap_tool_result(rpc)
    return {
        "ok": True,
        "source": SOURCE_ID,
        "status": "ok",
        "tool": tool,
        "data": data,
    }


def list_areas() -> Dict[str, Any]:
    return call_tool("list_areas", {})


def area_snapshot(area: Any, *, property_type: str = "Flat") -> Dict[str, Any]:
    if not configured():
        return _not_configured()
    try:
        alias = resolve_area(area)
        ptype = clean_text(property_type, field="property_type", limit=40) or "Flat"
    except InputRefused as exc:
        return {"ok": False, "source": SOURCE_ID, "status": "error", "error": str(exc)}
    out = call_tool(
        "area_snapshot",
        {"area": alias["resolved"], "property_type": ptype},
    )
    if out.get("ok"):
        out["area"] = alias
    return out


def rental_yield(area: Any, *, property_type: str = "Flat") -> Dict[str, Any]:
    if not configured():
        return _not_configured()
    try:
        alias = resolve_area(area)
        ptype = clean_text(property_type, field="property_type", limit=40) or "Flat"
    except InputRefused as exc:
        return {"ok": False, "source": SOURCE_ID, "status": "error", "error": str(exc)}
    out = call_tool(
        "rental_yield",
        {"area": alias["resolved"], "property_type": ptype},
    )
    if out.get("ok"):
        out["area"] = alias
    return out


def compare_areas(
    areas: Sequence[Any],
    *,
    property_type: str = "Flat",
) -> Dict[str, Any]:
    if not configured():
        return _not_configured()
    if not isinstance(areas, (list, tuple)) or len(areas) < 2:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": "areas must be a list of 2-5 area names",
        }
    if len(areas) > 5:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": "areas accepts at most 5 names",
        }
    try:
        resolved: List[str] = []
        aliases: List[Dict[str, str]] = []
        for item in areas:
            alias = resolve_area(item)
            aliases.append(alias)
            resolved.append(alias["resolved"])
        ptype = clean_text(property_type, field="property_type", limit=40) or "Flat"
    except InputRefused as exc:
        return {"ok": False, "source": SOURCE_ID, "status": "error", "error": str(exc)}
    out = call_tool("compare_areas", {"areas": resolved, "property_type": ptype})
    if out.get("ok"):
        out["areas"] = aliases
    return out


def market_overview() -> Dict[str, Any]:
    return call_tool("market_overview", {})
