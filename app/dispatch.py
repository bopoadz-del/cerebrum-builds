"""Block dispatch. Handlers call execute() here only. action= is a keyword."""

from __future__ import annotations

import asyncio
import importlib
import json
from typing import Any, Dict, Optional

from app.schema import SPECS
from vendor.cerebrum.blocks import get_block

# Harvested from vendor/blocks/*/block.json defaults + factory Store map.
BLOCK_DEFAULT_ACTIONS: Dict[str, str] = {
    "audit": "log",
    "dashboard": "render",
    "team": "create_team",
    "event_bus": "publish",
    "workflow": "run",
    "storage": "store",
    "vector_search": "search",
    "formula_executor": "execute",
    "capture": "extract",
    "spec_analyzer": "analyze",
    "estate_registry": "register",
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
    """Load a vendored Store block class. Used by the offline smoke probe."""
    return get_block(block_id)


def _instantiate(block_id: str) -> Any:
    block_cls = load_block(block_id)
    attempts = []
    for call in (
        lambda: block_cls(None, {}),
        lambda: block_cls(hal_block=None, config={}),
        lambda: block_cls(),
    ):
        try:
            return call()
        except TypeError as exc:
            attempts.append(exc)
    raise attempts[-1]


def execute(block_id: str, payload: Any = None, *, action: Optional[str] = None) -> Dict[str, Any]:
    """Run a vendored Store block. Pass action= as a keyword, never in payload."""
    if action is None:
        action = BLOCK_DEFAULT_ACTIONS.get(block_id)
    if action is None:
        raise RuntimeError("Unknown action: None")

    instance = _instantiate(block_id)
    params: Dict[str, Any] = {"action": action}
    body = payload if isinstance(payload, dict) else {}
    envelope = _run_async(instance.execute(body, params))
    if not isinstance(envelope, dict):
        envelope = {"result": envelope, "status": "success"}
    if envelope.get("status") == "error":
        inner = envelope.get("result", {})
        message = inner.get("error") if isinstance(inner, dict) else str(inner)
        raise RuntimeError(message or f"{block_id}: {action} failed")
    inner = envelope.get("result")
    if isinstance(inner, dict):
        err = str(inner.get("error") or "")
        if err.startswith("Unknown action"):
            raise RuntimeError(err)
    return envelope


def load_handler(capability_id: str):
    if capability_id not in SPECS:
        raise KeyError(capability_id)
    module = importlib.import_module(f"app.actions.{capability_id}")
    return module.handle


def dump_prepared(payload: Any) -> str:
    return json.dumps(payload, default=str)
