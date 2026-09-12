"""human_authority_gate — GENERATE. Human confirmation surface, no Store blocks."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: autonomous deploy / store publish

BLOCK_IDS: list[str] = []


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record a human-authority confirmation. High-impact actions stay pending."""
    record = {
        **payload,
        "authority": {
            "required": True,
            "confirmed": payload.get("status") == "closed",
            "actor_role": "operator",
        },
    }
    return ok_envelope("human_authority_gate", record)
