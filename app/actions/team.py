"""team — REUSE Store team block. Bind persist + BLOCK_DEFAULT_ACTIONS."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import team_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, env.process, config.runtime, team.state
# WRITES: caller.output, file.local.write
# NEVER: (none)

BLOCK_IDS = ["team"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a finance-ops working team from the envelope; persist the record."""
    blocks = {
        "team": execute(
            "team",
            team_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("team"),
        ),
    }
    return ok_envelope("team", payload, blocks)
