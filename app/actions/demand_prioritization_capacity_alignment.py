"""demand_prioritization_capacity_alignment — REUSE queue, team, formula, analytics."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, queue.jobs, team.state, config.runtime
# WRITES: caller.output, queue.jobs
# NEVER: inventing unverified Store block ids

BLOCK_IDS = ["queue", "team", "formula_executor", "analytics", "recommendation_template"]

STATUS_VALUES = ("open", "in_progress", "closed")
BAND_RANK = {"now": 1, "next": 2, "later": 3}
STAKEHOLDER = {"now": "joint_business_tech", "next": "tech_lead", "later": "backlog_steward"}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Rank a demand item and align capacity via Store queue/team/formula blocks."""
    status = str(payload.get("status") or "open")
    if status not in STATUS_VALUES:
        status = "open"
    band = str(payload.get("priority_band") or "now")
    if band not in BAND_RANK:
        band = "now"
    cost_of_delay = {"now": 21, "next": 13, "later": 5}[band]
    job_size = {"open": 8, "in_progress": 5, "closed": 2}[status]
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
        "demand_board": {
            "item": str(payload.get("demand_item") or payload.get("reference") or "sample"),
            "priority_band": band,
            "rank": BAND_RANK[band],
            "wsjf": int(round(cost_of_delay / job_size * 10)),
            "aligned_to": STAKEHOLDER[band],
            "resource_hold": band == "now" and status != "closed",
            "released": status == "closed",
        },
    }
    return ok_envelope("demand_prioritization_capacity_alignment", record, blocks)
