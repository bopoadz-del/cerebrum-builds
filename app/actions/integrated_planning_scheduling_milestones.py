"""integrated_planning_scheduling_milestones — REUSE workflow + prepared event_bus."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

from app.block_inputs import dashboard_input, event_bus_input, workflow_with_event_bus
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime
# WRITES: caller.output
# NEVER: forwarding the schema sample as an event_bus step input

BLOCK_IDS = ["workflow", "dashboard", "event_bus"]

STATUS_VALUES = ("open", "in_progress", "closed")
DEFAULT_PLANNED = date(2026, 9, 3)


def _planned(payload: Dict[str, Any]) -> date:
    raw = payload.get("planned_date")
    if raw in (None, "", "sample"):
        return DEFAULT_PLANNED
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return DEFAULT_PLANNED


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build an integrated milestone schedule and publish prepared event_bus steps."""
    status = str(payload.get("status") or "open")
    if status not in STATUS_VALUES:
        status = "open"
    planned = _planned(payload)
    slip = {"open": 21, "in_progress": 7, "closed": 0}[status]
    forecast = planned + timedelta(days=slip)
    name = str(payload.get("milestone_name") or payload.get("reference") or "sample")
    prepared_workflow = workflow_with_event_bus(
        payload,
        [
            ("airops.milestone.intake", f"milestone intake {name}"),
            ("airops.milestone.schedule", f"schedule {name} for {planned.isoformat()}"),
            ("airops.milestone.ready", f"readiness check {name}"),
        ],
    )
    blocks = {
        "workflow": execute(
            "workflow",
            prepared_workflow,
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
        "dashboard": execute(
            "dashboard",
            dashboard_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("dashboard"),
        ),
        "event_bus": execute(
            "event_bus",
            event_bus_input(payload, topic="airops.milestone.publish"),
            action=BLOCK_DEFAULT_ACTIONS.get("event_bus"),
        ),
    }
    record = {
        **payload,
        "status": status,
        "milestone_plan": {
            "name": name,
            "planned_date": planned.isoformat(),
            "forecast_date": forecast.isoformat(),
            "slip_days": slip,
            "on_critical_path": status != "closed",
            "schedule_basis": "integrated_planning",
            "channel": "mcp",
        },
    }
    return ok_envelope("integrated_planning_scheduling_milestones", record, blocks)
