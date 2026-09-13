"""delivery_kpi_adoption_analytics — REUSE analytics, knowledge, vector_search, memory."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.vector, memory.cache
# WRITES: caller.output, database.vector, memory.cache
# NEVER: inventing a second vector store

BLOCK_IDS = [
    "analytics",
    "dashboard",
    "knowledge",
    "vector_search",
    "recommendation_template",
    "memory",
]

STATUS_VALUES = ("open", "in_progress", "closed")
STREAM_TARGET = {"network": 100, "digital": 85, "erp": 70, "ops": 90}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Score a KPI against its value-stream target and run adoption analytics."""
    status = str(payload.get("status") or "open")
    if status not in STATUS_VALUES:
        status = "open"
    stream = str(payload.get("value_stream") or "network")
    if stream not in STREAM_TARGET:
        stream = "network"
    progress = {"open": 15, "in_progress": 55, "closed": 100}[status]
    target = STREAM_TARGET[stream]
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
        "kpi_card": {
            "kpi_name": str(payload.get("kpi_name") or payload.get("reference") or "sample"),
            "value_stream": stream,
            "target": target,
            "realized": int(round(target * progress / 100.0)),
            "gap": target - int(round(target * progress / 100.0)),
            "realization_pct": progress,
            "benefits_locked": status == "closed",
        },
    }
    return ok_envelope("delivery_kpi_adoption_analytics", record, blocks)
