"""preventive_maintenance — calendar → work order → bus. REUSE workflow + event_bus + queue."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import event_bus_input, queue_input, workflow_event_bus_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, memory.cache, queue.jobs
# WRITES: caller.output, queue.jobs
# NEVER: forwarding the schema sample as an event_bus step input

BLOCK_IDS = ["workflow", "event_bus", "queue"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run a prepared event_bus workflow (step_0, step_1, step_2), publish, and enqueue."""
    topics = [
        "preventive.scheduled",
        "preventive.dispatched",
        "preventive.escalated",
    ]
    workflow_input = workflow_event_bus_input(payload, topics)
    blocks = {
        "workflow": execute(
            "workflow",
            workflow_input,
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
        "event_bus": execute(
            "event_bus",
            event_bus_input(payload, "preventive.direct"),
            action=BLOCK_DEFAULT_ACTIONS.get("event_bus"),
        ),
        "queue": execute(
            "queue",
            queue_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("queue"),
        ),
    }
    return ok_envelope("preventive_maintenance", payload, blocks)
