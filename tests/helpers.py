"""Shared helpers for the suite.

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import store  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

TOKEN = "dev-local-token"
AUTH = {"Authorization": "Bearer " + TOKEN}
TENANT = "local"


def _value(cls, name: str) -> Any:
    """A value satisfying every constraint the field itself declares."""
    con = getattr(cls, "CONSTRAINTS", {}).get(name) or {}
    allowed = con.get("allowed_values")
    if allowed:
        return allowed[0]
    ann = str(getattr(cls, "__annotations__", {}).get(name, "str"))
    ann = ann.replace("Optional[", "").replace("]", "").strip()
    if ann in ("int", "float"):
        if con.get("min") is not None:
            return float(con["min"]) if ann == "float" else con["min"]
        return 1.0 if ann == "float" else 1
    if ann == "bool":
        return False
    low = name.lower()
    if low.endswith("_at") or low.endswith("_datetime"):
        return "2026-09-03T10:00:00"
    if low.endswith("_date"):
        return "2026-09-03"
    if low.endswith("_time"):
        return "10:00:00"
    if low == "status" or low.endswith("_status"):
        return "open"
    if low == "channel" or low.endswith("_channel"):
        return "mcp"
    return "sample"


def sample_for(capability_id: str) -> Dict[str, Any]:
    """A record built from the capability's own FIELDS + CONSTRAINTS."""
    from app.models import MODELS

    cls = MODELS[capability_id]
    return {name: _value(cls, name) for name in getattr(cls, "FIELDS", [])}


SAMPLES: Dict[str, Dict[str, Any]] = {}


def samples() -> Dict[str, Dict[str, Any]]:
    if not SAMPLES:
        from app.models import MODELS

        for capability_id in MODELS:
            SAMPLES[capability_id] = sample_for(capability_id)
    return SAMPLES


def client() -> TestClient:
    """A client that enters lifespan, so migrations and preconditions run."""
    return TestClient(app)


def entity_of(capability_id: str) -> str:
    from app.models import MODELS

    cls = MODELS[capability_id]
    return str(getattr(cls, "ENTITY", capability_id))


def rows(capability_id: str, tenant_id: str = TENANT) -> List[Dict[str, Any]]:
    return store.list_all(entity_of(capability_id), tenant_id)


def same(left: Any, right: Any) -> bool:
    """sqlite has no bool and stores 0/1; compare values, not spellings."""
    if isinstance(left, bool) or isinstance(right, bool):
        return int(bool(left)) == int(bool(right))
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return str(left) == str(right)


def listed(payload: Any) -> List[Dict[str, Any]]:
    """Pull the record list out of whatever shape a list route answers."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict) or payload.get("ok") is False:
        return []
    for key in ("items", "records", "results", "data", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []
