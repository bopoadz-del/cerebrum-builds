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
    "airport_readiness": _spec(
        "airport_readiness",
        ["analytics"],
        extra_fields={
            "stand_id": {"type": "string"},
            "readiness_window": {"type": "string"},
        },
        extra_constraints={
            "readiness_window": {
                "allowed_values": ["turnaround", "shift", "day"],
            },
        },
    ),
    "operational_dashboard": _spec(
        "operational_dashboard",
        ["dashboard", "analytics", "notification"],
        extra_fields={
            "view_name": {"type": "string"},
            "horizon": {"type": "string"},
        },
        extra_constraints={
            "horizon": {"allowed_values": ["today", "week", "month"]},
        },
    ),
    "ground_workflow_coordination": _spec(
        "ground_workflow_coordination",
        ["workflow", "team", "queue"],
        extra_fields={
            "crew_name": {"type": "string"},
            "work_order": {"type": "string"},
        },
    ),
    "regulatory_document_control": _spec(
        "regulatory_document_control",
        ["document_engine", "validation", "audit", "storage"],
        extra_fields={
            "document_title": {"type": "string"},
            "control_class": {"type": "string"},
        },
        extra_constraints={
            "control_class": {
                "allowed_values": ["manual", "certificate", "directive"],
            },
        },
    ),
    "incident_evidence_tracking": _spec(
        "incident_evidence_tracking",
        ["capture", "file_hasher", "storage"],
        extra_fields={
            "incident_note": {"type": "string"},
            "evidence_kind": {"type": "string"},
        },
        extra_constraints={
            "evidence_kind": {
                "allowed_values": ["photo", "report", "sensor"],
            },
        },
    ),
    "flight_event_orchestration": _spec(
        "flight_event_orchestration",
        ["event_bus", "workflow", "notification", "queue"],
        extra_fields={
            "event_type": {"type": "string"},
            "flight_reference": {"type": "string"},
        },
        extra_constraints={
            "event_type": {
                "allowed_values": ["arrival", "departure", "weather", "hold"],
            },
        },
    ),
    "airport_knowledge_assistant": _spec(
        "airport_knowledge_assistant",
        ["knowledge", "vector_search", "recommendation_template", "memory"],
        extra_fields={
            "question": {"type": "string"},
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
