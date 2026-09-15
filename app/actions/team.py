"""team — REUSE Store team. Branch sales desks and headcount."""

from __future__ import annotations

import secrets
from typing import Any, Dict

from app.block_inputs import team_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import (
    allowed_next_status,
    desk_headcount,
    desk_name,
    envelope_status,
)
from app.persist import ok_envelope

# READS: caller.input, file.local.read, env.process, config.runtime, team.state
# WRITES: caller.output, file.local.write
# NEVER: (none)

BLOCK_IDS = ["team"]
CAPABILITY_ID = "team"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Open a branch sales desk and persist the team roster row."""
    payload = dict(payload or {})
    status = envelope_status(payload)
    desk = desk_name(payload)
    branch = str(payload.get("branch") or payload.get("reference") or "sample")
    headcount = desk_headcount(desk)
    record = {
        **payload,
        "reference": str(payload.get("reference") or "sample"),
        "status": status,
        "desk": desk,
        "branch": branch,
        "headcount": headcount,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    prepared = team_input(record)
    prepared["name"] = f"Auto {desk} {branch} {secrets.token_hex(3)}"
    prepared["user_id"] = str(record.get("actor") or record.get("user_id") or "operator")
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepared,
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["roster"] = {
        "desk": desk,
        "branch": branch,
        "headcount": headcount,
        "allowed_next_status": list(allowed_next_status(status)),
        "plan": "free",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
