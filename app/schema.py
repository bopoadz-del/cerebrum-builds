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
    "aircraft_maintenance_tracking": _spec(
        "aircraft_maintenance_tracking",
        ["workflow", "audit"],
        extra_fields={
            "tail_number": {"type": "string"},
            "work_order_kind": {"type": "string"},
        },
        extra_constraints={
            "work_order_kind": {
                "allowed_values": ["scheduled", "unscheduled", "ad_directive"],
            },
        },
    ),
    "regulatory_compliance_audit": _spec(
        "regulatory_compliance_audit",
        ["audit", "file_hasher"],
        extra_fields={
            "regulation": {"type": "string"},
            "finding_severity": {"type": "string"},
        },
        extra_constraints={
            "regulation": {
                "allowed_values": ["part_121", "part_135", "easa_ops"],
            },
            "finding_severity": {
                "allowed_values": ["observation", "minor", "major"],
            },
        },
    ),
    "fleet_registry_management": _spec(
        "fleet_registry_management",
        ["database", "validation"],
        extra_fields={
            "registration": {"type": "string"},
            "aircraft_type": {"type": "string"},
        },
        extra_constraints={
            "aircraft_type": {
                "allowed_values": ["narrowbody", "widebody", "bizjet"],
            },
        },
    ),
    "crew_training_readiness": _spec(
        "crew_training_readiness",
        ["team", "notification", "workflow"],
        extra_fields={
            "crew_role": {"type": "string"},
            "currency_item": {"type": "string"},
        },
        extra_constraints={
            "crew_role": {
                "allowed_values": ["captain", "first_officer", "cabin"],
            },
            "currency_item": {
                "allowed_values": ["line_check", "sim", "crm"],
            },
        },
    ),
    "flight_document_control": _spec(
        "flight_document_control",
        ["document_engine", "storage", "file_hasher", "notification"],
        extra_fields={
            "document_kind": {"type": "string"},
            "revision": {"type": "string"},
        },
        extra_constraints={
            "document_kind": {
                "allowed_values": ["mel", "qrh", "weight_balance", "release"],
            },
        },
    ),
    "operational_analytics_dashboard": _spec(
        "operational_analytics_dashboard",
        ["dashboard", "analytics"],
        extra_fields={
            "view_name": {"type": "string"},
            "horizon": {"type": "string"},
        },
        extra_constraints={
            "horizon": {"allowed_values": ["today", "week", "month"]},
        },
    ),
    "safety_knowledge_assistant": _spec(
        "safety_knowledge_assistant",
        ["knowledge", "vector_search", "memory"],
        extra_fields={
            "question": {"type": "string"},
            "corpus_layer": {"type": "string"},
        },
        extra_constraints={
            "corpus_layer": {"allowed_values": ["sms", "asrs", "fom"]},
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
