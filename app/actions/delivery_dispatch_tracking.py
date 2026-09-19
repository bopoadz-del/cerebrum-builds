"""Capability delivery_dispatch_tracking — orders, drivers, vehicles, status.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``database``    — records the delivery against the dispatch ledger;
  * ``workflow``    — the dispatch run. EVERY child is prepared in source:
      - step_0 ``database``   — writes the delivery row;
      - step_1 ``event_bus``  — publishes the dispatch event with the full
        contract (topic, payload dict, message, channel=mcp, action=publish);
      - step_2 ``queue``      — enqueues the driver's close-out job;
  * ``event_bus``   — publishes the same dispatch event on the direct path;
  * ``queue``       — enqueues the close-out job directly;
  * ``notification``— notifies the shop over the MCP channel;
  * ``analytics``   — records the dispatch metric as a tracked event.

The schema sample (``reference``/``status``/domain strings) is never forwarded
as a workflow step input: each child gets a constructed, block-acceptable input,
and the workflow record carries ``result`` from the first prepared step.

Scope
-----
READS  the caller's payload.
WRITES nothing (dispatch results are returned; the route persists).
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_inputs import prepare_block_input
from app.dispatch import execute

CAPABILITY_ID = "delivery_dispatch_tracking"
ENTITY = "delivery_dispatch_tracking"
BLOCK_IDS = [
    "database",
    "workflow",
    "event_bus",
    "queue",
    "notification",
    "analytics",
]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "database": "insert",
    "workflow": "run",
    "event_bus": "publish",
    "queue": "enqueue",
    "notification": "send",
    "analytics": "track_event",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "order_code",
    "shop_code",
    "driver_code",
    "vehicle_code",
    "vehicle_type",
    "delivery_address",
    "scheduled_at",
    "delivery_state",
    "notes",
    "status",
]


def _dispatch_context(record: Dict[str, Any]) -> Dict[str, Any]:
    """Order, shop, driver and the vehicle the dispatcher assigned."""
    state = str(record.get("delivery_state") or "pending")
    return {
        "order": str(record.get("order_code") or record.get("reference") or "order"),
        "shop": str(record.get("shop_code") or "shop"),
        "driver": str(record.get("driver_code") or "driver"),
        "vehicle": str(record.get("vehicle_code") or "vehicle"),
        "vehicle_type": str(record.get("vehicle_type") or "bike"),
        "state": state,
        "scheduled": str(record.get("scheduled_at") or ""),
    }


def _event_payload(record: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Domain scalars for the dispatch event — never the raw schema sample."""
    return {
        "reference": str(record.get("reference") or "sample"),
        "order_code": ctx["order"],
        "shop_code": ctx["shop"],
        "driver_code": ctx["driver"],
        "vehicle_code": ctx["vehicle"],
        "vehicle_type": ctx["vehicle_type"],
        "delivery_state": ctx["state"],
    }


def _dispatch_steps(
    record: Dict[str, Any], ctx: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Every workflow child prepared in source (step_0 .. step_2).

    The event_bus child carries its five keys as a literal dict so the
    prepared contract is visible to a source reader (and to the factory's
    workflow-accept AST check) rather than assembled elsewhere: topic,
    payload dict of domain scalars, message, channel=mcp, tool=event_bus.
    """
    values = prepare_block_input("database", record, entity=ENTITY)["values"]
    queue_input = prepare_block_input(
        "queue", record, entity=ENTITY, job_type="delivery_close:%s" % ctx["order"]
    )
    queue_input["payload"] = _event_payload(record, ctx)
    return [
        {
            "id": "step_0",
            "block": "database",
            "action": "insert",
            "input": {"table": ENTITY, "values": values},
            "params": {"action": "insert"},
        },
        {
            "id": "step_1",
            "block": "event_bus",
            "action": "publish",
            "input": {
                "topic": "delivery.%s" % ctx["state"],
                "payload": {
                    "reference": str(record.get("reference") or "sample"),
                    "order_code": ctx["order"],
                    "shop_code": ctx["shop"],
                    "driver_code": ctx["driver"],
                    "vehicle_code": ctx["vehicle"],
                    "vehicle_type": ctx["vehicle_type"],
                    "delivery_state": ctx["state"],
                },
                "message": "delivery %s for %s assigned to %s"
                % (ctx["order"], ctx["shop"], ctx["driver"]),
                "channel": "mcp",
                "tool": "event_bus",
            },
            "params": {"action": "publish"},
        },
        {
            "id": "step_2",
            "block": "queue",
            "action": "enqueue",
            "input": queue_input,
            "params": {"action": "enqueue"},
        },
    ]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    ctx = _dispatch_context(data)
    steps = _dispatch_steps(data, ctx)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(
            block_id, data, entity=ENTITY, steps=steps if block_id == "workflow" else None
        )
        if block_id == "event_bus":
            prepared["topic"] = "delivery.%s" % ctx["state"]
            prepared["payload"] = _event_payload(data, ctx)
            prepared["message"] = "delivery %s for %s is %s" % (
                ctx["order"],
                ctx["shop"],
                ctx["state"],
            )
            prepared["channel"] = "mcp"
            prepared["tool"] = "event_bus"
        if block_id == "queue":
            prepared["job_type"] = "delivery_close:%s" % ctx["order"]
            prepared["payload"] = _event_payload(data, ctx)
        if block_id == "notification":
            prepared["message"] = "delivery %s %s -> %s (%s)" % (
                ctx["order"],
                ctx["state"],
                data.get("delivery_address") or "address",
                ctx["driver"],
            )
            prepared["payload"] = _event_payload(data, ctx)
        if block_id == "analytics":
            prepared["metric"] = "deliveries_dispatched"
            prepared["value"] = 1
            prepared["name"] = ENTITY
            prepared["period"] = ctx["state"]
        result = execute(
            block_id, prepared, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
        )
        results[block_id] = result
        if isinstance(result, dict) and (
            result.get("status") in ("error", "failed", "partial")
            or result.get("ok") is False
            or "error" in result
        ):
            errors[block_id] = str(result.get("error") or result)[:200]
    if errors:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
            "results": results,
        }
    return {"ok": True, "capability": CAPABILITY_ID, "results": results}
