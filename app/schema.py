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
    "veterinary_care_core": _spec(
        "veterinary_care_core",
        ["analytics"],
        extra_fields={
            "clinic_unit": {"type": "string"},
            "caseload_window": {"type": "string"},
        },
        extra_constraints={
            "caseload_window": {
                "allowed_values": ["walk_in", "shift", "day"],
            },
        },
    ),
    "patient_records_management": _spec(
        "patient_records_management",
        ["knowledge", "vector_search", "memory"],
        extra_fields={
            "patient_name": {"type": "string"},
            "species": {"type": "string"},
        },
        extra_constraints={
            "species": {
                "allowed_values": ["canine", "feline", "exotic", "equine"],
            },
        },
    ),
    "appointment_scheduling": _spec(
        "appointment_scheduling",
        ["workflow", "event_bus", "notification", "queue"],
        extra_fields={
            "visit_type": {"type": "string"},
            "slot_label": {"type": "string"},
        },
        extra_constraints={
            "visit_type": {
                "allowed_values": ["wellness", "surgery", "emergency", "follow_up"],
            },
        },
    ),
    "prescription_management": _spec(
        "prescription_management",
        ["validation", "analytics"],
        extra_fields={
            "medication_name": {"type": "string"},
            "dose_form": {"type": "string"},
        },
        extra_constraints={
            "dose_form": {
                "allowed_values": ["tablet", "liquid", "injectable"],
            },
        },
    ),
    "billing_and_invoicing": _spec(
        "billing_and_invoicing",
        ["validation", "notification", "queue"],
        extra_fields={
            "invoice_kind": {"type": "string"},
            "line_label": {"type": "string"},
        },
        extra_constraints={
            "invoice_kind": {
                "allowed_values": ["consult", "procedure", "pharmacy"],
            },
        },
    ),
    "client_communication_portal": _spec(
        "client_communication_portal",
        ["notification", "event_bus", "knowledge"],
        extra_fields={
            "message_kind": {"type": "string"},
            "client_name": {"type": "string"},
        },
        extra_constraints={
            "message_kind": {
                "allowed_values": ["reminder", "result", "billing"],
            },
        },
    ),
    "audit": _spec(
        "audit",
        ["audit"],
        extra_fields={
            "event_category": {"type": "string"},
            "resource_label": {"type": "string"},
        },
        extra_constraints={
            "event_category": {
                "allowed_values": ["clinical", "billing", "access"],
            },
        },
    ),
    "dashboard": _spec(
        "dashboard",
        ["dashboard", "analytics"],
        extra_fields={
            "view_name": {"type": "string"},
            "horizon": {"type": "string"},
        },
        extra_constraints={
            "horizon": {"allowed_values": ["today", "week", "month"]},
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
