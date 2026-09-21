"""Handler for capability mcp_adapter.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

The MCP surface reads the block catalogue: which blocks this platform
carries, what each one declares, and therefore which tools an MCP client may
call. The vendored ``mcp_adapter`` block is the reader; where the delivery's
registry cannot be enumerated (see docs/blockers.json) the capability falls
back to the contract file this build ships (``docs/block_contracts.json``),
which is generated from the same block metadata, and names the block as
unavailable rather than reporting an empty catalogue as complete.

The block's ``never`` scope forbids tool invocation -- this capability lists
and describes, it never calls a tool through the adapter.

Scope
-----
READS  this capability's own columns from the caller's record; the vendored
       block catalogue (``vendor/blocks/*/block.json``, read-only);
       ``docs/block_contracts.json``; app.dispatch (the local offline block
       runtime); app.store (the ``mcp_adapter`` table, through the route's
       tenant-scoped save).
WRITES app.dispatch.execute() results; exactly one row in ``mcp_adapter`` via
       the ROUTE's ``store.save(entity, record, tenant_id)`` -- this handler
       has no tenant and never persists directly.
NEVER  invoking a block as an MCP tool (``block:tool_invocation``); unguarded
       network egress; ``vendor/**`` writes (sealed, read-only); another
       capability's table; ``tests/**``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.block_run import block_runner, probe_block
from app.security import InputRefused, clean_text

CAPABILITY_ID = "mcp_adapter"
ENTITY = "mcp_adapter"
BLOCK_IDS = ['mcp_adapter']
#: The adapter dispatches on ``list_tools`` / ``describe``; listing is the
#: read this capability is allowed to perform.
BLOCK_DEFAULT_ACTIONS = {'mcp_adapter': 'list_tools'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'tool_name', 'catalog_scope', 'request_shape',
    'response_shape', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'catalog_scope': {'allowed_values': ['platform', 'vendor', 'tenant'],
                      'required': True},
}


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def _contract_catalog() -> List[Dict[str, Any]]:
    """The catalogue this build ships, used when the block cannot enumerate."""
    path = Path(__file__).resolve().parents[2] / "docs" / "block_contracts.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    blocks = data.get("blocks") if isinstance(data, dict) else None
    if isinstance(blocks, list):
        return [item for item in blocks if isinstance(item, dict)]
    if isinstance(blocks, dict):
        return [
            {"block_id": key, **(value if isinstance(value, dict) else {})}
            for key, value in blocks.items()
        ]
    return []


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "mcp-adapter"
        tool_name = _text(data, "tool_name", 200)
        scope = _text(data, "catalog_scope", 40).lower() or "platform"
        if scope not in EDGE_CONSTRAINTS['catalog_scope']['allowed_values']:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "catalog_scope must be one of: "
                         + ", ".join(EDGE_CONSTRAINTS['catalog_scope']['allowed_values']),
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    probed = probe_block(
        "mcp_adapter",
        {"tool_name": tool_name, "catalog_scope": scope},
        action="list_tools",
        entity=ENTITY,
        roster=BLOCK_IDS,
        default_actions=BLOCK_DEFAULT_ACTIONS,
    )
    tools: List[Any] = []
    unavailable: Dict[str, str] = {}
    catalog_source = "mcp_adapter"
    if probed["ok"]:
        raw_tools = probed["result"].get("tools") or probed["result"].get("items")
        tools = raw_tools if isinstance(raw_tools, list) else []
    else:
        unavailable["mcp_adapter"] = probed["error"]
        catalog = _contract_catalog()
        tools = catalog
        catalog_source = "docs/block_contracts.json"

    describing = bool(tool_name)
    described = next(
        (item for item in tools
         if isinstance(item, dict) and str(item.get("block_id") or item.get("name")) == tool_name),
        None,
    ) if describing else None

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "catalog_scope": scope,
        "tool_name": tool_name,
        "tool_count": len(tools),
        "tools": [item.get("block_id") or item.get("name") for item in tools if isinstance(item, dict)][:50],
        "described": described,
        "catalog_source": catalog_source,
        "request_shape": {"method": "tools/list", "params": {"scope": scope}},
        "response_shape": {"tools": "array", "tool": tool_name or "*"},
        "invoked_tool": False,
        "blocks_unavailable": unavailable,
        "blocker": "" if probed["ok"] else (
            "mcp_adapter block cannot enumerate the registry in this delivery; "
            "the committed block contract file carries the catalogue"
        ),
        "blocks": runner.report() or [
            {"block": "mcp_adapter", "action": "list_tools", "ok": probed["ok"],
             "error": probed["error"]}
        ],
    }
