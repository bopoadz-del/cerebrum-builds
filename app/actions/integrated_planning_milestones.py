"""integrated_planning_milestones — GENERATE. Planning, scheduling, milestone dates."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
DEFAULT_PLANNED = date(2026, 9, 3)


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _planned(payload: Dict[str, Any]) -> date:
    raw = payload.get("planned_date")
    if raw in (None, "", "sample"):
        return DEFAULT_PLANNED
    if isinstance(raw, date) and not isinstance(raw, type(DEFAULT_PLANNED)):
        return raw
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return DEFAULT_PLANNED


def _offset_days(status: str) -> int:
    return {"open": 21, "in_progress": 7, "closed": 0}[status]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build an integrated milestone schedule from the envelope date and status."""
    status = _status(payload)
    planned = _planned(payload)
    forecast = planned + timedelta(days=_offset_days(status))
    name = str(payload.get("milestone_name") or payload.get("reference") or "sample")
    record = {
        **payload,
        "status": status,
        "milestone_plan": {
            "name": name,
            "planned_date": planned.isoformat(),
            "forecast_date": forecast.isoformat(),
            "slip_days": (forecast - planned).days,
            "on_critical_path": status != "closed",
            "schedule_basis": "integrated_planning",
            "channel": "mcp",
        },
    }
    return ok_envelope("integrated_planning_milestones", record)
