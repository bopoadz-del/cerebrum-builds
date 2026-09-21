"""Block input construction: a domain record becomes a block-acceptable call.

A block's contract asks for named inputs, not for this platform's columns.
This module is the one place that translation happens, so a handler can call
a block without inventing the block's argument names, and a block called
with the wrong action is refused by name rather than silently returning
nothing.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Sequence

#: The action each block is called with when a caller does not name one.
STORE_BLOCK_DEFAULT_ACTIONS: Dict[str, str] = {
    "capture": "parse",
    "queue": "enqueue",
    "workflow": "transition",
    "event_bus": "append",
    "knowledge": "ingest",
    "vector_search": "query",
    "evidence_or_refuse": "answer",
    "ingestion_provenance": "record",
    "validation": "record",
    "recommendation_template": "summary",
    "audit_chain": "verify",
    "database": "list",
    "storage": "list",
    "local_drive": "list",
    "webhook": "post",
    "notification": "send",
    "mock_connector_bus": "shape",
    "formula_executor": "run",
    "llm_enhancer": "turn",
    "agent_state_sync": "get",
    "orchestrator": "run",
    "twilio_programmable_voice": "twiml",
    "chart_renderer": "bars",
    "mcp_adapter": "tools/list",
}

#: Input names each block's contract expects, in the order it reads them.
BLOCK_INPUT_KEYS: Dict[str, Sequence[str]] = {
    "capture": ("text", "content", "file_name", "ocr_languages"),
    "queue": ("capability_id", "item", "tenant_id", "idempotency_key"),
    "workflow": ("call_sid", "event", "previous_state", "language"),
    "event_bus": ("tenant_id", "call_sid", "event_type", "detail", "outcome"),
    "knowledge": ("tenant_id", "text", "title", "project_tag", "certified", "document_id"),
    "vector_search": ("tenant_id", "question", "project_tag", "top_k", "claim_type"),
    "evidence_or_refuse": ("tenant_id", "project_tag", "question", "claim_type", "language"),
    "notification": ("trigger_event", "channel", "target", "subject", "body", "summary"),
    "webhook": ("url", "payload"),
    "formula_executor": ("formula", "inputs"),
    "local_drive": ("tenant_id", "relative_path", "content"),
    "google_drive": ("operation", "folder_id", "document_id", "file_name"),
    "mcp_adapter": ("method", "tool", "arguments", "tenant_id"),
}

#: Keys that are routing, never domain data.
SKIP_KEYS = ("ok", "error", "capability", "capability_id", "id", "status", "result", "payload", "block")


def default_block_action(block_id: str, default_actions: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """The action for a block, from the caller's map or this platform's."""
    bid = str(block_id or "").strip()
    if isinstance(default_actions, Mapping):
        candidate = default_actions.get(bid)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    mapped = STORE_BLOCK_DEFAULT_ACTIONS.get(bid)
    return mapped.strip() if isinstance(mapped, str) and mapped.strip() else None


def prepare_block_input(
    block_id: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    action: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the input a block accepts from a domain record.

    A named input is taken from the payload when present; otherwise the whole
    record travels under ``record`` so the block can still see it. Structured
    values are passed as JSON text, which is what the blocks serialise.
    """
    body = {str(k): v for k, v in dict(payload or {}).items()}
    bid = str(block_id or "")
    prepared: Dict[str, Any] = {"action": action or default_block_action(bid)}
    keys = BLOCK_INPUT_KEYS.get(bid)
    if keys:
        for key in keys:
            if key in body and body[key] not in (None, ""):
                prepared[key] = body[key]
    for key, value in body.items():
        if key in SKIP_KEYS or key in prepared:
            continue
        if key.isupper():
            # A credential or setting is configuration, not an input.
            continue
        prepared.setdefault("record", {})[key] = value
    if "record" in prepared and not isinstance(prepared["record"], dict):
        prepared["record"] = json.loads(json.dumps(prepared["record"], default=str))
    prepared["block"] = bid
    return prepared


def block_contract(block_id: str) -> Dict[str, Any]:
    from app import dispatch

    entry = dispatch.BLOCKS.get(str(block_id))
    if entry is None:
        raise KeyError(f"unknown block: {block_id}")
    return {
        "block_id": entry["block_id"],
        "actions": list(entry["actions"]),
        "default_action": default_block_action(block_id),
        "inputs": list(BLOCK_INPUT_KEYS.get(str(block_id), ())),
        "description": entry["description"],
    }
