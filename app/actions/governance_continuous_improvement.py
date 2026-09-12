"""governance_continuous_improvement — GENERATE. Ownership, discipline, feedback loop."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
SOURCE_ACTION = {
    "stakeholder": "intake_review",
    "rte": "inspect_adapt",
    "operator": "ops_retro",
}
DISCIPLINE = ("clear_ownership", "delivery_cadence", "feedback_loop")


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _source(payload: Dict[str, Any]) -> str:
    value = str(payload.get("feedback_source") or "stakeholder")
    return value if value in SOURCE_ACTION else "stakeholder"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record a governance item and the continuous-improvement action it opens."""
    status = _status(payload)
    source = _source(payload)
    record = {
        **payload,
        "status": status,
        "governance": {
            "owner_name": str(payload.get("owner_name") or payload.get("reference") or "sample"),
            "feedback_source": source,
            "next_action": SOURCE_ACTION[source],
            "disciplines": list(DISCIPLINE),
            "loop_open": status != "closed",
            "improvement_logged": True,
        },
    }
    return ok_envelope("governance_continuous_improvement", record)
