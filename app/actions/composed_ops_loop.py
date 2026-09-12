"""composed_ops_loop — GAP. Registry + maintenance + readiness loop authored here."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified estate_* block ids

BLOCK_IDS: list[str] = []


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compose an ops-loop ticket from the envelope without calling missing blocks."""
    record = {
        **payload,
        "loop": {
            "registry": payload.get("reference"),
            "maintenance": "queued",
            "readiness": "pending" if payload.get("status") != "closed" else "cleared",
        },
    }
    return ok_envelope("composed_ops_loop", record)
