"""crew_training_readiness — REUSE team + notification + workflow. Currency board."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import notification_input, team_input, workflow_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, env.process, config.runtime, team.state,
#        network.http.outbound, credential.env, block.peer
# WRITES: caller.output, file.local.write, network.smtp.outbound, email.outbound,
#         notification.outbound
# NEVER: (none)

BLOCK_IDS = ["team", "notification", "workflow"]

ROLE_CURRENCY_DAYS = {
    "captain": 180,
    "first_officer": 180,
    "cabin": 365,
    "dispatcher": 365,
}
READINESS_HOLD = {"current": False, "due": True, "expired": True}


def _role(payload: Dict[str, Any]) -> str:
    value = str(payload.get("crew_role") or "captain")
    return value if value in ROLE_CURRENCY_DAYS else "captain"


def _readiness(payload: Dict[str, Any]) -> str:
    value = str(payload.get("readiness") or "current")
    return value if value in READINESS_HOLD else "current"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Stand up a crew training cell, notify MCP, and run the readiness workflow."""
    role = _role(payload)
    readiness = _readiness(payload)
    reference = str(payload.get("reference") or "sample")
    team_name = f"Crew training {role} {reference}"
    note = f"Training currency {readiness} for {role} on {reference}"
    team_body = team_input(payload, team_name)
    notify_body = notification_input(payload, note)
    steps = [
        {
            "id": "step_0",
            "block": "team",
            "action": "create_team",
            "params": {"action": BLOCK_DEFAULT_ACTIONS.get("team")},
            "input": team_body,
        },
        {
            "id": "step_1",
            "block": "notification",
            "action": "send",
            "params": {"action": BLOCK_DEFAULT_ACTIONS.get("notification")},
            "input": notify_body,
        },
    ]
    first_result = steps[0]["input"]
    blocks = {
        "team": execute(
            "team",
            team_body,
            action=BLOCK_DEFAULT_ACTIONS.get("team"),
        ),
        "notification": execute(
            "notification",
            notify_body,
            action=BLOCK_DEFAULT_ACTIONS.get("notification"),
        ),
        "workflow": execute(
            "workflow",
            workflow_input(payload, steps, f"crew-{reference}"),
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
    }
    record = {
        **payload,
        "training_card": {
            "crew_role": role,
            "readiness": readiness,
            "currency_days": ROLE_CURRENCY_DAYS[role],
            "hold_from_line": READINESS_HOLD[readiness],
            "channel": "mcp",
            "result": first_result,
        },
    }
    return ok_envelope("crew_training_readiness", record, blocks)
