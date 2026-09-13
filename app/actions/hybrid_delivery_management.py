"""hybrid_delivery_management — REUSE workflow, team, queue, dashboard, validation."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, team.state, queue.jobs, config.runtime
# WRITES: caller.output, queue.jobs, file.local.write
# NEVER: inventing unverified Store block ids

BLOCK_IDS = ["workflow", "team", "queue", "dashboard", "validation"]

STATUS_VALUES = ("open", "in_progress", "closed")
ROLE_LANE = {
    "rte": "train_sync",
    "scrum_master": "iteration",
    "pm": "waterfall_control",
    "ba": "discovery",
}
MODE_BLEND = {
    "hybrid": ("pi_planning", "stage_gate"),
    "agile": ("sprint", "increment"),
    "waterfall": ("phase", "gate"),
}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Assign a hybrid delivery lane and owner discipline from the envelope."""
    status = str(payload.get("status") or "open")
    if status not in STATUS_VALUES:
        status = "open"
    role = str(payload.get("owner_role") or "rte")
    if role not in ROLE_LANE:
        role = "rte"
    mode = str(payload.get("delivery_mode") or "hybrid")
    if mode not in MODE_BLEND:
        mode = "hybrid"
    ceremonies = MODE_BLEND[mode]
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepare_block_input(block_id, payload),
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record = {
        **payload,
        "status": status,
        "delivery_board": {
            "owner_role": role,
            "lane": ROLE_LANE[role],
            "delivery_mode": mode,
            "ceremonies": list(ceremonies),
            "cadence": "pi_plus_gate" if mode == "hybrid" else ceremonies[0],
            "reference": str(payload.get("reference") or "sample"),
            "can_exit_phase": status == "in_progress",
            "is_terminal": status == "closed",
        },
    }
    return ok_envelope("hybrid_delivery_management", record, blocks)
