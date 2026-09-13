"""data_synchronization — REUSE event_bus + queue + database. Offline sync."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import database_input, event_bus_input, queue_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql, queue.jobs
# WRITES: caller.output, queue.jobs, database.sql
# NEVER: channel=sample; HTTP store callbacks; inventing a RAG surface here

BLOCK_IDS = ["event_bus", "queue", "database"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Publish a sync event, enqueue the job, query the local table; persist."""
    published = execute(
        "event_bus",
        event_bus_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("event_bus"),
    )
    queued = execute(
        "queue",
        queue_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("queue"),
    )
    queried = execute(
        "database",
        database_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("database"),
    )
    record = {
        **payload,
        "sync": {
            "source_name": payload.get("source_name") or "sample",
            "sync_mode": payload.get("sync_mode") or "push",
            "channel": "mcp",
            "job": (queued.get("result") or {}).get("id") if isinstance(queued, dict) else None,
        },
    }
    return ok_envelope(
        "data_synchronization",
        record,
        {"event_bus": published, "queue": queued, "database": queried},
    )
