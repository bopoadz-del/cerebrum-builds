"""Capability specs. Envelope vocabulary is schema-enforced: open | in_progress | closed."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

STATUS_VALUES = ("open", "in_progress", "closed")
RESERVED_FIELDS = frozenset({"action", "id"})

ENVELOPE_FIELDS: Dict[str, Dict[str, Any]] = {
    "reference": {"type": "string"},
    "status": {"type": "string"},
}

ENVELOPE_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    "status": {"allowed_values": list(STATUS_VALUES)},
}


def _spec(
    capability_id: str,
    block_ids: List[str],
    extra_fields: Mapping[str, Dict[str, Any]] | None = None,
    extra_constraints: Mapping[str, Dict[str, Any]] | None = None,
    entity: str | None = None,
) -> Dict[str, Any]:
    fields = {**ENVELOPE_FIELDS, **(extra_fields or {})}
    constraints = {**ENVELOPE_CONSTRAINTS, **(extra_constraints or {})}
    return {
        "id": capability_id,
        "entity": entity or capability_id,
        "FIELDS": fields,
        "CONSTRAINTS": constraints,
        "BLOCK_IDS": list(block_ids),
    }


SPECS: Dict[str, Dict[str, Any]] = {
    "inventory_tracking": _spec(
        "inventory_tracking",
        ["database", "validation", "audit"],
        extra_fields={
            "sku": {"type": "string"},
            "quantity_on_hand": {"type": "int"},
            "reorder_threshold": {"type": "int"},
        },
        extra_constraints={
            "quantity_on_hand": {"min": 0},
            "reorder_threshold": {"min": 0},
        },
    ),
    "order_management": _spec(
        "order_management",
        ["workflow", "queue", "database", "notification"],
        extra_fields={
            "order_number": {"type": "string"},
            "fulfillment_stage": {"type": "string"},
        },
        extra_constraints={
            "fulfillment_stage": {
                "allowed_values": ["received", "picking", "packed", "shipped"],
            },
        },
    ),
    "ops_dashboard": _spec(
        "ops_dashboard",
        ["dashboard", "analytics", "database"],
        extra_fields={
            "view_name": {"type": "string"},
            "horizon": {"type": "string"},
        },
        extra_constraints={
            "horizon": {"allowed_values": ["today", "week", "month"]},
        },
    ),
    "stock_alerts": _spec(
        "stock_alerts",
        ["notification", "event_bus"],
        extra_fields={
            "sku": {"type": "string"},
            "alert_kind": {"type": "string"},
        },
        extra_constraints={
            "alert_kind": {
                "allowed_values": ["below_reorder", "stalled_order"],
            },
        },
    ),
    "pilot_ops_log": _spec(
        "pilot_ops_log",
        ["knowledge", "memory", "storage"],
        extra_fields={
            "note_title": {"type": "string"},
            "note_body": {"type": "string"},
        },
    ),
}

CAPABILITIES = SPECS
REQUIRED_CAPABILITY_IDS = tuple(SPECS.keys())


def get_spec(capability_id: str) -> Dict[str, Any]:
    try:
        return SPECS[capability_id]
    except KeyError as exc:
        raise KeyError(f"unknown capability: {capability_id}") from exc
