"""aircraft_maintenance_tracking — REUSE workflow + audit. Airworthiness work orders."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["workflow", "audit"]
CAPABILITY_ID = "aircraft_maintenance_tracking"
WORK_KINDS = ("scheduled", "unscheduled", "ad_directive")
MEL_LIMITS = {"scheduled": 120, "unscheduled": 72, "ad_directive": 24}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Open a maintenance work order, run the mx pipeline, and audit the event."""
    kind = str(payload.get("work_order_kind") or "scheduled")
    if kind not in WORK_KINDS:
        kind = "scheduled"
    tail = str(payload.get("tail_number") or payload.get("reference") or "sample")
    hours_remaining = MEL_LIMITS[kind]
    airworthy = payload.get("status") != "closed" and hours_remaining > 0
    record = {
        **payload,
        "tail_number": tail,
        "work_order_kind": kind,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepare_block_input(block_id, record),
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["maintenance"] = {
        "tail_number": tail,
        "kind": kind,
        "hours_remaining": hours_remaining,
        "airworthy": airworthy,
        "pipeline": "mx-control",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
