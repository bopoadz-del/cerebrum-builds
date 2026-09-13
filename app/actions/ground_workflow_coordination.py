"""ground_workflow_coordination — REUSE workflow + team + queue."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, team.state, queue.jobs
# WRITES: caller.output, file.local.write, queue.jobs
# NEVER: (none)

BLOCK_IDS = ["workflow", "team", "queue"]
CAPABILITY_ID = "ground_workflow_coordination"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a ground crew: pipeline, team roster, and airside queue."""
    crew_name = str(payload.get("crew_name") or payload.get("reference") or "sample")
    work_order = str(payload.get("work_order") or payload.get("reference") or "sample")
    record = {
        **payload,
        "crew_name": crew_name,
        "work_order": work_order,
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
    record["dispatch"] = {
        "crew_name": crew_name,
        "work_order": work_order,
        "queued": True,
        "pipeline": f"ground-{record.get('reference') or 'sample'}",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
