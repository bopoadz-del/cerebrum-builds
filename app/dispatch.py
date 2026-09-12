"""Block dispatch. Handlers call execute() here only. action= is a keyword."""

from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
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
}


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
        return None
    from vendor.cerebrum.blocks import get_block
    from vendor.cerebrum.blocks.workflow import _instantiate_store_block

    block_cls = get_block(block_id)
    from vendor.cerebrum.blocks.workflow import _offline_hal

    extra = {}
    if block_id == "knowledge":
        extra["vector_db_url"] = ""
    try:
        return block_cls(_offline_hal(), extra)
    except TypeError:
        return _instantiate_store_block(block_cls)


def _prepare_workflow_payload(payload: Any) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    if "result" not in data:
        steps = data.get("steps") or []
        first_input = {}
        if steps and isinstance(steps[0], dict):
            first_input = dict(steps[0].get("input") or {})
        data["result"] = first_input.get("payload") or {"reference": data.get("reference", "sample")}
    prepared_steps = []
    for idx, step in enumerate(data.get("steps") or []):
        if not isinstance(step, dict):
            continue
        item = dict(step)
        block_name = item.get("block") or item.get("block_id")
        action = item.get("action") or (item.get("params") or {}).get("action")
        if block_name == "event_bus":
            action = action or "publish"
            inp = dict(item.get("input") or {})
            inp.setdefault("topic", str(data.get("reference") or f"event_{idx}"))
            if not isinstance(inp.get("payload"), dict):
                inp["payload"] = {"reference": data.get("reference", "sample")}
            inp.setdefault("message", str(data.get("reference") or "estate event"))
            inp["channel"] = "mcp"
            inp["tool"] = "event_bus"
            if "result" not in inp:
                inp["result"] = data.get("result") or {}
            item["input"] = inp
            item["block"] = "event_bus"
            item["action"] = "publish"
        params = dict(item.get("params") or {})
        if action:
            params["action"] = action
        item["params"] = params
        item.setdefault("id", f"step_{idx}")
        prepared_steps.append(item)
    data["steps"] = prepared_steps
    return data


def execute(block_id: str, payload: Any = None, *, action: Optional[str] = None) -> Dict[str, Any]:
    """Run a vendored Store block. Pass action= as a keyword, never in payload."""
    if action is None:
        action = BLOCK_DEFAULT_ACTIONS.get(block_id)
    if action is None:
        raise RuntimeError("Unknown action: None")

    if block_id == "workflow":
        payload = _prepare_workflow_payload(payload)

    if block_id == "capture":
        from vendor.blocks.capture.block import run as capture_run

        result = capture_run(input=payload, action=action)
        return {"block": "capture", "status": "success", "result": result}

    instance = _instantiate(block_id)
    params: Dict[str, Any] = {"action": action}
    if block_id == "vector_search":
        params["operation"] = action
    if block_id == "knowledge":
        params.setdefault("llm_provider", "none")
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


def storage_tempfile(name: str, body: bytes) -> str:
    from app.store import storage_root

    path = storage_root() / "tmp" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return str(path)
