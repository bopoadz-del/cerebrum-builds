"""team_management — REUSE team, audit."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input, team_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, env.process, config.runtime, team.state, database.sql
# WRITES: caller.output, file.local.write, database.sql
# NEVER: (none)

BLOCK_IDS = ["team", "audit"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a shop crew from the envelope and audit the membership change."""
    record = {**payload, "capability": "team_management"}
    blocks = {
        "team": execute(
            "team",
            team_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("team"),
        ),
        "audit": execute(
            "audit",
            audit_input({**record, "event_action": "team_upsert", "category": "admin"}),
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
    }
    return ok_envelope("team_management", record, blocks)
