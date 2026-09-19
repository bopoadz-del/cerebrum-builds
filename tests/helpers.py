"""Shared test helpers (schema-sample payload + authenticated client)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PLATFORM_TOKEN = os.environ.get("PLATFORM_TOKEN", "dev-local-token")
AUTH = {"Authorization": "Bearer " + PLATFORM_TOKEN}


def sample_payload(capability_id: str) -> Dict[str, Any]:
    """The payload the factory's schema probe builds: FIELDS + CONSTRAINTS."""
    from app.models import MODELS

    cls = MODELS[capability_id]
    body: Dict[str, Any] = {name: "sample" for name in cls.FIELDS}
    for name, rules in (cls.CONSTRAINTS or {}).items():
        allowed = rules.get("allowed_values")
        if allowed:
            body[name] = allowed[0]
        fmt = str(rules.get("format") or "")
        if fmt == "date":
            body[name] = "2026-09-03"
        elif fmt == "datetime":
            body[name] = "2026-09-03T10:00:00"
        elif fmt == "time":
            body[name] = "10:00:00"
        if name.endswith("_at") and "T" not in str(body.get(name, "")):
            body[name] = "2026-09-03T10:00:00"
        if name.endswith("_date") and fmt != "datetime":
            body[name] = "2026-09-03"
    return body


def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
