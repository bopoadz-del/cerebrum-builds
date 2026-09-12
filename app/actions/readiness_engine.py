"""readiness_engine — GAP. Property readiness gate before activation."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: unlisted Store block ids

BLOCK_IDS: list[str] = []


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a readiness verdict from the envelope status vocabulary."""
    status = payload.get("status", "open")
    ready = status == "closed"
    record = {
        **payload,
        "readiness": "ready" if ready else "blocked",
        "gate": "guest_or_staff_activation",
    }
    return ok_envelope("readiness_engine", record)
