"""staff_scheduling — household shifts. REUSE workflow + team + notification."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import notification_input, team_input, workflow_event_bus_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, env.process, config.runtime, team.state
# WRITES: caller.output, file.local.write, notification.outbound
# NEVER: unprepared event_bus workflow children

BLOCK_IDS = ["workflow", "team", "notification"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule a shift: prepared workflow children, team create, MCP notify."""
    workflow_input = workflow_event_bus_input(
        payload,
        ["staff.shift_opened", "staff.assigned", "staff.notified"],
    )
    blocks = {
        "workflow": execute(
            "workflow",
            workflow_input,
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
        "team": execute(
            "team",
            team_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("team"),
        ),
        "notification": execute(
            "notification",
            notification_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("notification"),
        ),
    }
    return ok_envelope("staff_scheduling", payload, blocks)
