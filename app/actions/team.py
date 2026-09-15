"""team — REUSE team. Per-branch sales / service / finance desks."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import team_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, desk_kind_of, envelope_status, seat_count
from app.persist import ok_envelope

# READS: caller.input, file.local.read, env.process, config.runtime, team.state
# WRITES: caller.output, file.local.write
# NEVER: (none)

BLOCK_IDS = ["team"]
CAPABILITY_ID = "team"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Open a dealership desk and persist the branch roster."""
    status = envelope_status(payload)
    desk_kind = desk_kind_of(payload)
    desk_name = str(payload.get("desk_name") or payload.get("reference") or "sample")
    seats = seat_count(desk_kind)
    record = {
        **payload,
        "status": status,
        "desk_kind": desk_kind,
        "desk_name": desk_name,
        "seat_count": seats,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    prepared = team_input(record)
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepared,
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["desk"] = {
        "desk_kind": desk_kind,
        "desk_name": desk_name,
        "seat_count": seats,
        "team_named": f"Desk {desk_name}",
        "allowed_next_status": list(allowed_next_status(status)),
        "listed": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
