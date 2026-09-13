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
    "inventory_stock_tracking": _spec(
        "inventory_stock_tracking",
        ["database", "storage", "validation", "audit"],
        extra_fields={
            "sku": {"type": "string"},
            "product_name": {"type": "string"},
            "quantity": {"type": "int"},
            "location": {"type": "string"},
        },
        extra_constraints={
            "quantity": {"min": 0},
        },
    ),
    "low_stock_alerts": _spec(
        "low_stock_alerts",
        ["notification", "event_bus", "queue"],
        extra_fields={
            "sku": {"type": "string"},
            "product_name": {"type": "string"},
            "threshold": {"type": "int"},
        },
        extra_constraints={
            "threshold": {"min": 0},
        },
    ),
    "team_management": _spec(
        "team_management",
        ["team", "audit"],
        extra_fields={
            "member_name": {"type": "string"},
            "member_role": {"type": "string"},
            "shop_name": {"type": "string"},
        },
        extra_constraints={
            "member_role": {"allowed_values": ["operator", "admin"]},
        },
    ),
    "inventory_dashboard": _spec(
        "inventory_dashboard",
        ["dashboard", "analytics"],
        extra_fields={
            "shop_name": {"type": "string"},
            "horizon": {"type": "string"},
        },
        extra_constraints={
            "horizon": {"allowed_values": ["daily", "weekly", "monthly"]},
        },
    ),
    "stock_adjustment_workflow": _spec(
        "stock_adjustment_workflow",
        ["workflow", "audit", "validation"],
        extra_fields={
            "sku": {"type": "string"},
            "adjustment_qty": {"type": "int"},
            "reason": {"type": "string"},
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
