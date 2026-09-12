"""portfolio_rollup — GAP. Roll up readiness and maintenance across estates."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: unlisted Store block ids

BLOCK_IDS: list[str] = []


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a portfolio rollup row keyed by the incoming reference."""
    record = {
        **payload,
        "rollup": {
            "estates": 1,
            "open_signals": 0 if payload.get("status") == "closed" else 1,
            "source": "authored_gap",
        },
    }
    return ok_envelope("portfolio_rollup", record)
