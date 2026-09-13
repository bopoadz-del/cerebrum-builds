"""Block dispatch. Handlers call execute() here only. action= is a keyword."""

from __future__ import annotations

import asyncio
import importlib
import json
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
    "estate_registry": "register",
    "readiness_engine": "assess",
    "memory": "get",
    "file_hasher": "hash",
}


class _CaptureAdapter:
    """Vendored capture is a run() adapter, not a cerebrum registry class."""

    name = "capture"
    version = "1.0.0"

    async def execute(self, input_data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        from vendor.blocks.capture.block import run

        data = input_data if isinstance(input_data, dict) else {"text": str(input_data or "")}
        result = run(input=data)
        return {"block": "capture", "status": "success", "result": result}


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(asyncio.run, coro).result()


def _instantiate(block_id: str) -> Any:
    if block_id == "capture":
        return _CaptureAdapter()
    from vendor.blocks.audit.block import _instantiate_store_block
    from vendor.cerebrum.blocks import get_block

    block_cls = get_block(block_id)
    return _instantiate_store_block(block_cls)


def _wrap_workflow_input(payload: Any) -> Any:
    """Factory wrap: copy step.action into params; attach result for Store shims."""
    if not isinstance(payload, dict):
        return payload
    wrapped = dict(payload)
    steps = wrapped.get("steps")
    if not isinstance(steps, list):
        return wrapped
    prepared_steps = []
    for step in steps:
        if not isinstance(step, dict):
            prepared_steps.append(step)
            continue
        child = dict(step)
        block_name = child.get("block") or child.get("block_id")
        child_action = child.get("action") or BLOCK_DEFAULT_ACTIONS.get(block_name)
        if child_action:
            child["action"] = child_action
            params = dict(child.get("params") or {})
            params.setdefault("action", child_action)
            child["params"] = params
        prepared_steps.append(child)
    wrapped["steps"] = prepared_steps
    if "result" not in wrapped:
        first = prepared_steps[0] if prepared_steps else {}
        first_input = first.get("input") if isinstance(first, dict) else {}
        if isinstance(first_input, dict):
            wrapped["result"] = first_input.get("payload") or first_input
        else:
            wrapped["result"] = {"reference": "sample"}
    first = prepared_steps[0] if prepared_steps else None
    if isinstance(first, dict) and isinstance(first.get("input"), dict):
        step_input = dict(first["input"])
        if "result" not in step_input:
            step_input["result"] = wrapped["result"]
        first["input"] = step_input
        prepared_steps[0] = first
        wrapped["steps"] = prepared_steps
    return wrapped


def execute(block_id: str, payload: Any = None, *, action: Optional[str] = None) -> Dict[str, Any]:
    """Run a vendored Store block. Pass action= as a keyword, never in payload."""
    if action is None:
        action = BLOCK_DEFAULT_ACTIONS.get(block_id)
    if action is None:
        raise RuntimeError("Unknown action: None")

    if block_id == "workflow":
        payload = _wrap_workflow_input(payload)

    instance = _instantiate(block_id)
    params: Dict[str, Any] = {"action": action}
    if block_id == "vector_search":
        params.setdefault("operation", action)
    envelope = _run_async(instance.execute(payload, params))
    if isinstance(envelope, dict) and envelope.get("status") == "error":
        inner = envelope.get("result", {})
        message = inner.get("error") if isinstance(inner, dict) else str(inner)
        raise RuntimeError(message or f"{block_id}: {action} failed")
    return envelope if isinstance(envelope, dict) else {"result": envelope, "status": "success"}


def load_handler(capability_id: str):
    if capability_id not in SPECS:
        raise KeyError(capability_id)
    module = importlib.import_module(f"app.actions.{capability_id}")
    return module.handle


def dump_prepared(payload: Any) -> str:
    return json.dumps(payload, default=str)
