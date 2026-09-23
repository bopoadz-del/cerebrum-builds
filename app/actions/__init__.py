"""CallOps capability handlers: one module per capability id.

``handle_for`` resolves a capability id to its module without the caller
needing to know the import path — the HTTP routes, the MCP adapter and the
queue processor all dispatch through here.
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Dict, Optional

from app.models import MODELS

_CACHE: Dict[str, ModuleType] = {}


def handle_for(capability_id: str) -> ModuleType:
    key = str(capability_id)
    if key not in MODELS:
        raise KeyError(f"unknown capability: {capability_id}")
    module = _CACHE.get(key)
    if module is None:
        module = importlib.import_module(f"app.actions.{key}")
        if getattr(module, "CAPABILITY_ID", None) != key:
            raise ImportError(f"app/actions/{key}.py declares the wrong CAPABILITY_ID")
        if not callable(getattr(module, "handle", None)):
            raise ImportError(f"app/actions/{key}.py has no handle()")
        _CACHE[key] = module
    return module


def handle(capability_id: str, payload: dict) -> dict:
    return handle_for(capability_id).handle(dict(payload or {}))


def loaded() -> list:
    return sorted(_CACHE)
