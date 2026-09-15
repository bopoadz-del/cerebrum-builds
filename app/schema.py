"""Capability specs. Envelope vocabulary is schema-enforced: open | in_progress | closed."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

STATUS_VALUES = ("open", "in_progress", "closed")
RESERVED_FIELDS = frozenset({"action", "id"})
NOTE_OPS = ("create", "update", "delete", "search")

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
    "productivity_core": _spec(
        "productivity_core",
        [],
        extra_fields={
            "title": {"type": "string"},
            "body": {"type": "string"},
            "keyword": {"type": "string"},
            "note_op": {"type": "string"},
        },
        extra_constraints={
            "note_op": {"allowed_values": list(NOTE_OPS)},
        },
    ),
    "audit": _spec(
        "audit",
        ["audit"],
        extra_fields={
            "event_action": {"type": "string"},
            "resource": {"type": "string"},
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


def schema_sample(capability_id: str) -> Dict[str, Any]:
    """Payload the writer_behaviour / PRODUCT probes build from FIELDS + CONSTRAINTS."""
    spec = get_spec(capability_id)
    payload: Dict[str, Any] = {}
    for name, meta in spec["FIELDS"].items():
        constraint = spec["CONSTRAINTS"].get(name) or {}
        allowed = constraint.get("allowed_values")
        if allowed:
            payload[name] = allowed[0]
        elif name == "status" or name.endswith("_status"):
            payload[name] = "open"
        elif name == "channel" or name.endswith("_channel"):
            payload[name] = "email"
        elif "email" in name:
            payload[name] = "sample@example.com"
        elif meta.get("type") == "int" or meta.get("type") == "integer":
            payload[name] = constraint.get("min", 1)
        elif meta.get("type") == "float":
            payload[name] = constraint.get("min", 1)
        elif meta.get("type") == "bool" or meta.get("type") == "boolean":
            payload[name] = False
        else:
            payload[name] = "sample"
    payload["reference"] = payload.get("reference") or "sample"
    payload["status"] = payload.get("status") or "open"
    return payload
