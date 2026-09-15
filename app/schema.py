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
    "automotive_core": _spec(
        "automotive_core",
        [],
        extra_fields={
            "condition": {"type": "string"},
            "branch": {"type": "string"},
        },
        extra_constraints={
            "condition": {"allowed_values": ["new", "used"]},
        },
    ),
    "dashboard": _spec(
        "dashboard",
        ["dashboard"],
        extra_fields={
            "view_name": {"type": "string"},
            "horizon": {"type": "string"},
        },
        extra_constraints={
            "horizon": {"allowed_values": ["today", "week", "month"]},
        },
    ),
    "team": _spec(
        "team",
        ["team"],
        extra_fields={
            "desk": {"type": "string"},
            "branch": {"type": "string"},
        },
        extra_constraints={
            "desk": {"allowed_values": ["sales", "finance", "service"]},
        },
    ),
    "audit": _spec(
        "audit",
        ["audit"],
        extra_fields={
            "category": {"type": "string"},
            "note": {"type": "string"},
        },
        extra_constraints={
            "category": {"allowed_values": ["data_access", "auth", "system", "admin"]},
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
