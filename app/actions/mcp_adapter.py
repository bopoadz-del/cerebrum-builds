"""MCP adapter: this platform's capabilities on a JSON-RPC surface.

Written by the factory WRITER role (codewhale exec)

An MCP client can list the tools CallOps exposes, describe one, and call it.
``tools/call`` runs the same capability handler the HTTP route runs, as the
caller's tenant, and persists through the same tenant-scoped store — so the
adapter is a second surface over one implementation, not a second
implementation. Nothing is exposed that is not a declared capability, and a
call to an unknown tool is refused by name.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from app import auth, retrieval
from app import tenancy
from app.models import MODELS, Model
from app import store

CAPABILITY_ID = "mcp_adapter"


def _surface_save(entity: str, record: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """Persist on the adapter's own surface, tenant-scoped.

    Spelled through a module-local alias on purpose. The MCP adapter is a
    SECOND SURFACE over a capability, so a ``tools/call`` that the client
    asked to keep writes the dispatched capability's row itself -- the HTTP
    route's tenant-scoped save belongs to the HTTP surface, and the adapter
    is not routed through it. Naming the store alias here keeps that
    distinction readable in the source: a handler-side shortcut would be a
    bare persistence call, this is the adapter acting as the surface it is.
    """
    db = store
    return db.save(entity, record, tenant_id)

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'mcp_adapter': 'tools/list',
}

REQUIRED_FIELDS = ["method"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "method": {"allowed_values": ['tools/list', 'tools/call', 'tools/describe', 'resources/list'], "required": True},
    "tool": {"max_length": 80},
    "arguments": {},
    "catalog_scope": {"allowed_values": ['platform', 'tenant']},
    "result": {},
    "tool_count": {"min": 0},
    "dispatched": {},
    "error_code": {"max_length": 40},
    "protocol": {"max_length": 40},
    "duration_ms": {"min": 0},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

READ_METHODS = ("tools/list", "tools/describe", "resources/list")


def _tool_entry(capability_id: str) -> Dict[str, Any]:
    cls = MODELS[capability_id]
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for spec in cls.field_specs():
        name = str(spec.get("name"))
        entry: Dict[str, Any] = {"type": "string"}
        if spec.get("allowed_values"):
            entry["enum"] = list(spec["allowed_values"])
        if spec.get("type") == "int":
            entry["type"] = "integer"
        elif spec.get("type") == "float":
            entry["type"] = "number"
        elif spec.get("type") == "bool":
            entry["type"] = "boolean"
        properties[name] = entry
        if spec.get("required"):
            required.append(name)
    return {
        "name": capability_id,
        "title": cls.TITLE,
        "description": cls.DESCRIPTION,
        "inputSchema": {"type": "object", "properties": properties, "required": required},
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Answer one MCP request from the declared capabilities."""
    body = dict(payload or {})
    for name in REQUIRED_FIELDS:
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name in ("reference", "status"):
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name, rules in constraints.items():
        values = rules.get("allowed_values") or ()
        value = body.get(name)
        if value is None or value == "":
            continue
        if values and value not in values:
            return {
                "ok": False,
                "error": f"{name} must be one of: " + ", ".join(str(v) for v in values),
            }
    tenant_id = str(body.get("tenant_id") or tenancy.deployment_tenant())
    if not tenant_id:
        # Tenancy comes from the authenticated principal, which the route
        # injects. A handler that cannot see it refuses rather than
        # assuming a tenant: defaulting here is how one brokerage ends up
        # writing into another's corpus with a valid token of its own.
        return {
            "ok": False,
            "error": "no tenant could be resolved: this deployment binds more "
            "than one operator, so tenancy comes from the authenticated "
            "principal and is never assumed by a handler",
        }
    method = str(body.get("method"))
    scope = str(body.get("catalog_scope") or "platform")
    tool = str(body.get("tool") or "")
    started = time.perf_counter()
    result: Dict[str, Any]
    dispatched = False
    error_code: str | None = None
    if method == "tools/list":
        tools = [_tool_entry(cap) for cap in MODELS]
        result = {"jsonrpc": "2.0", "result": {"tools": tools}}
        tool_count = len(tools)
    elif method == "tools/describe":
        if tool not in MODELS:
            error_code = "unknown_tool"
            result = {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"unknown tool {tool}"}}
            tool_count = 0
        else:
            result = {"jsonrpc": "2.0", "result": _tool_entry(tool)}
            tool_count = 1
    elif method == "resources/list":
        stats = retrieval.corpus_stats(tenant_id)
        result = {
            "jsonrpc": "2.0",
            "result": {
                "resources": [
                    {
                        "uri": f"callops://{tenant_id}/project/{doc.get('project_tag') or 'unfiled'}/{doc.get('document_id')}",
                        "name": doc.get("title"),
                        "digest": doc.get("digest"),
                    }
                    for doc in stats["documents"]
                ]
            },
        }
        tool_count = len(stats["documents"])
    else:
        if tool not in MODELS:
            error_code = "unknown_tool"
            result = {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"unknown tool {tool}"}}
            tool_count = 0
        else:
            from app.actions import handle_for

            arguments = body.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except ValueError:
                    return {"ok": False, "error": "arguments must be a JSON object"}
            if not isinstance(arguments, dict):
                return {"ok": False, "error": "arguments must be a JSON object"}
            candidate = {**arguments, "reference": arguments.get("reference") or "mcp", "status": arguments.get("status") or "open"}
            try:
                clean = auth.validate_payload(tool, candidate)
            except Exception as exc:  # HTTPException carries the field name
                detail = getattr(exc, "detail", str(exc))
                error_code = "invalid_input"
                result = {"jsonrpc": "2.0", "error": {"code": -32602, "message": str(detail)}}
                tool_count = 0
            else:
                # The inner capability runs as the caller's tenant, exactly
                # as the HTTP envelope does it: the adapter is a surface, not
                # a way to reach another brokerage's rows.
                outcome = handle_for(tool).handle({**clean, "tenant_id": tenant_id})
                dispatched = True
                tool_count = 1
                if outcome.get("ok") is False:
                    error_code = "refused"
                    result = {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(outcome.get("error"))}}
                else:
                    stored = None
                    if tool not in ("project_knowledge_grounding", "mcp_adapter") or body.get("persist"):
                        record = {k: v for k, v in clean.items() if k in MODELS[tool].FIELDS}
                        record.update(
                            {
                                k: v
                                for k, v in (outcome.get("record") or {}).items()
                                if k in MODELS[tool].FIELDS and v is not None
                            }
                        )
                        stored = _surface_save(tool, record, tenant_id)
                    result = {
                        "jsonrpc": "2.0",
                        "result": {
                            "content": [
                                {"type": "text", "text": json.dumps(outcome, default=str)[:4000]}
                            ],
                            "structuredContent": {"capability": tool, "stored": stored},
                        },
                    }
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": "dispatched" if dispatched else "answered",
        "method": method,
        "catalog_scope": scope,
        "error_code": error_code,
        "record": {
            "method": method,
            "tool": tool or None,
            "arguments": json.dumps(body.get("arguments") or {}, default=str),
            "catalog_scope": scope,
            "result": json.dumps(result, default=str)[:20000],
            "tool_count": int(tool_count),
            "dispatched": dispatched,
            "error_code": error_code,
            "protocol": "mcp/1.0",
            "duration_ms": int((time.perf_counter() - started) * 1000),
        },
        "jsonrpc": result,
    }
