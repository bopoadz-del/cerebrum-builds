"""Capability specs. Envelope vocabulary is schema-enforced: open | in_progress | closed."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

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
    "productivity_core": _spec(
        "productivity_core",
        [],
        extra_fields={
            "title": {"type": "string"},
            "body": {"type": "string"},
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


def validate_payload(capability_id: str, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], None] | Tuple[None, str]:
    """Accept empty {} (code-phase / schema-sample probe). Enforce envelope on any keys."""
    if capability_id not in SPECS:
        return None, "unknown capability"
    if not isinstance(payload, dict):
        return None, "payload must be an object"
    reserved = RESERVED_FIELDS.intersection(payload)
    if reserved:
        return None, f"reserved-keyword fields refused: {sorted(reserved)}"
    spec = SPECS[capability_id]
    fields = spec["FIELDS"]
    constraints = spec["CONSTRAINTS"]
    if payload:
        missing = [name for name in ("reference", "status") if name not in payload]
        if missing:
            return None, f"missing required field: {missing[0]}"
        status = payload.get("status")
        allowed = (constraints.get("status") or {}).get("allowed_values") or list(STATUS_VALUES)
        if status not in allowed:
            return None, f"status must be one of {allowed}"
        for name, meta in constraints.items():
            if name == "status" or name not in payload:
                continue
            allowed_values = meta.get("allowed_values")
            if allowed_values and payload[name] not in allowed_values:
                return None, f"{name} must be one of {allowed_values}"
        for name, meta in fields.items():
            if name in payload and meta.get("type") == "string" and payload[name] is None:
                return None, f"{name} must be a string"
    return payload, None
