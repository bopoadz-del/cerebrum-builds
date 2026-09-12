"""demand_prioritization_resources — GENERATE. Demand ranking and resource alignment."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
BAND_RANK = {"now": 1, "next": 2, "later": 3}
STAKEHOLDER = {"now": "joint_business_tech", "next": "tech_lead", "later": "backlog_steward"}


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _band(payload: Dict[str, Any]) -> str:
    value = str(payload.get("priority_band") or "now")
    return value if value in BAND_RANK else "now"


def _wsjf(band: str, status: str) -> int:
    cost_of_delay = { "now": 21, "next": 13, "later": 5 }[band]
    job_size = {"open": 8, "in_progress": 5, "closed": 2}[status]
    return int(round(cost_of_delay / job_size * 10))


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Rank a demand item and name the aligning business/tech stakeholder."""
    status = _status(payload)
    band = _band(payload)
    record = {
        **payload,
        "status": status,
        "demand_board": {
            "item": str(payload.get("demand_item") or payload.get("reference") or "sample"),
            "priority_band": band,
            "rank": BAND_RANK[band],
            "wsjf": _wsjf(band, status),
            "aligned_to": STAKEHOLDER[band],
            "resource_hold": band == "now" and status != "closed",
            "released": status == "closed",
        },
    }
    return ok_envelope("demand_prioritization_resources", record)
