"""Block dispatch. Handlers call execute() here only. action= is a keyword."""

from __future__ import annotations

import asyncio
import importlib
from typing import Any, Dict, Optional

from app.schema import SPECS

# Harvested from vendor/blocks/*/block.json defaults + factory Store map.
BLOCK_DEFAULT_ACTIONS: Dict[str, str] = {
    "database": "query",
    "storage": "store",
    "validation": "validate_pipeline",
    "document_engine": "parse",
    "knowledge": "ask",
    "vector_search": "search",
    "formula_executor": "execute",
    "audit": "log",
    "notification": "send",
    "workflow": "run",
    "event_bus": "publish",
    "queue": "enqueue",
    "team": "create_team",
    "dashboard": "render",
    "analytics": "track_event",
    "spec_analyzer": "analyze",
    "recommendation_template": "recommend",
    "capture": "extract",
    "file_hasher": "hash",
    "estate_registry": "register",
    "readiness_engine": "assess",
    "memory": "get",
}


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(asyncio.run, coro).result()


def load_block(block_id: str) -> Any:
    from vendor.cerebrum.blocks import get_block

    return get_block(block_id)


def _instantiate(block_id: str) -> Any:
    from vendor.blocks.audit.block import _instantiate_store_block

    return _instantiate_store_block(load_block(block_id))


def execute(block_id: str, payload: Any = None, *, action: Optional[str] = None) -> Dict[str, Any]:
    """Run a vendored Store block. Pass action= as a keyword, never in payload."""
    if action is None:
        action = BLOCK_DEFAULT_ACTIONS.get(block_id)
    if action is None:
        raise RuntimeError("Unknown action: None")

    instance = _instantiate(block_id)
    params: Dict[str, Any] = {"action": action}
    envelope = _run_async(instance.execute(payload if payload is not None else {}, params))
    if not isinstance(envelope, dict):
        return {"result": envelope, "status": "success"}
    inner = envelope.get("result", {})
    message = None
    if envelope.get("status") == "error":
        message = inner.get("error") if isinstance(inner, dict) else str(inner)
    elif isinstance(inner, dict) and inner.get("error"):
        message = str(inner.get("error"))
    if message:
        raise RuntimeError(message)
    return envelope


def load_handler(capability_id: str):
    if capability_id not in SPECS:
        raise KeyError(capability_id)
    module = importlib.import_module(f"app.actions.{capability_id}")
    return module.handle
