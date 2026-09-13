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
    "aviation_core": _spec(
        "aviation_core",
        [],
        extra_fields={
            "carrier_code": {"type": "string"},
            "hub_city": {"type": "string"},
        },
        extra_constraints={
            "carrier_code": {"allowed_values": ["RX"]},
            "hub_city": {"allowed_values": ["Riyadh"]},
        },
    ),
    "audit": _spec("audit", ["audit"]),
    "dashboard": _spec("dashboard", ["dashboard"]),
    "enterprise_portfolio_dashboard": _spec(
        "enterprise_portfolio_dashboard",
        [],
        extra_fields={
            "initiative_name": {"type": "string"},
            "horizon": {"type": "string"},
        },
        extra_constraints={
            "horizon": {"allowed_values": ["strategic", "tactical", "runway"]},
        },
    ),
    "hybrid_program_delivery": _spec(
        "hybrid_program_delivery",
        [],
        extra_fields={
            "owner_role": {"type": "string"},
            "delivery_mode": {"type": "string"},
        },
        extra_constraints={
            "owner_role": {"allowed_values": ["rte", "scrum_master", "pm", "ba"]},
            "delivery_mode": {"allowed_values": ["hybrid", "agile", "waterfall"]},
        },
    ),
    "integrated_planning_milestones": _spec(
        "integrated_planning_milestones",
        [],
        extra_fields={
            "milestone_name": {"type": "string"},
            "planned_date": {"type": "date"},
        },
    ),
    "kpi_value_realization": _spec(
        "kpi_value_realization",
        [],
        extra_fields={
            "kpi_name": {"type": "string"},
            "value_stream": {"type": "string"},
        },
        extra_constraints={
            "value_stream": {"allowed_values": ["network", "digital", "erp", "ops"]},
        },
    ),
    "budget_capacity_oversight": _spec(
        "budget_capacity_oversight",
        [],
        extra_fields={
            "budget_code": {"type": "string"},
            "currency": {"type": "string"},
        },
        extra_constraints={
            "currency": {"allowed_values": ["SAR", "USD"]},
        },
    ),
    "demand_prioritization_resources": _spec(
        "demand_prioritization_resources",
        [],
        extra_fields={
            "demand_item": {"type": "string"},
            "priority_band": {"type": "string"},
        },
        extra_constraints={
            "priority_band": {"allowed_values": ["now", "next", "later"]},
        },
    ),
    "oracle_erp_program_oversight": _spec(
        "oracle_erp_program_oversight",
        [],
        extra_fields={
            "workstream": {"type": "string"},
            "suite_module": {"type": "string"},
        },
        extra_constraints={
            "workstream": {"allowed_values": ["erp_delivery", "integration", "cutover"]},
            "suite_module": {"allowed_values": ["finance", "procurement", "hcm"]},
        },
    ),
    "gdpr_privacy_audit": _spec(
        "gdpr_privacy_audit",
        ["audit"],
        extra_fields={
            "lawful_basis": {"type": "string"},
            "data_subject": {"type": "string"},
        },
        extra_constraints={
            "lawful_basis": {
                "allowed_values": [
                    "legitimate_interest",
                    "consent",
                    "contract",
                    "legal_obligation",
                ]
            },
        },
    ),
    "governance_continuous_improvement": _spec(
        "governance_continuous_improvement",
        [],
        extra_fields={
            "owner_name": {"type": "string"},
            "feedback_source": {"type": "string"},
        },
        extra_constraints={
            "feedback_source": {"allowed_values": ["stakeholder", "rte", "operator"]},
        },
    ),
    "airline_ops_portfolio_context": _spec(
        "airline_ops_portfolio_context",
        [],
        extra_fields={
            "station": {"type": "string"},
            "framing": {"type": "string"},
        },
        extra_constraints={
            "station": {"allowed_values": ["RUH", "JED", "DMM"]},
            "framing": {"allowed_values": ["portfolio", "ops_context"]},
        },
    ),
    "aircraft_maintenance_tracking": _spec(
        "aircraft_maintenance_tracking",
        ["workflow", "audit"],
        extra_fields={
            "tail_number": {"type": "string"},
            "maintenance_kind": {"type": "string"},
        },
        extra_constraints={
            "maintenance_kind": {
                "allowed_values": ["scheduled", "unscheduled", "ad_compliance"]
            },
        },
    ),
    "regulatory_compliance_audit": _spec(
        "regulatory_compliance_audit",
        ["audit", "file_hasher"],
        extra_fields={
            "regulation": {"type": "string"},
            "audit_scope": {"type": "string"},
        },
        extra_constraints={
            "regulation": {"allowed_values": ["far_121", "easa_part_ops", "gaca"]},
            "audit_scope": {"allowed_values": ["airworthiness", "ops", "training"]},
        },
    ),
    "fleet_registry_management": _spec(
        "fleet_registry_management",
        ["database", "validation"],
        extra_fields={
            "aircraft_type": {"type": "string"},
            "registry_mark": {"type": "string"},
        },
        extra_constraints={
            "aircraft_type": {
                "allowed_values": ["narrow_body", "wide_body", "regional", "rotorcraft"]
            },
        },
    ),
    "crew_training_readiness": _spec(
        "crew_training_readiness",
        ["team", "notification", "workflow"],
        extra_fields={
            "crew_role": {"type": "string"},
            "readiness": {"type": "string"},
        },
        extra_constraints={
            "crew_role": {
                "allowed_values": ["captain", "first_officer", "cabin", "dispatcher"]
            },
            "readiness": {"allowed_values": ["current", "due", "expired"]},
        },
    ),
    "flight_document_control": _spec(
        "flight_document_control",
        ["document_engine", "storage", "file_hasher", "notification"],
        extra_fields={
            "document_class": {"type": "string"},
            "control_state": {"type": "string"},
        },
        extra_constraints={
            "document_class": {"allowed_values": ["amm", "mel", "qrh", "ops_manual"]},
            "control_state": {"allowed_values": ["controlled", "draft", "superseded"]},
        },
    ),
    "operational_analytics_dashboard": _spec(
        "operational_analytics_dashboard",
        ["dashboard", "analytics"],
        extra_fields={
            "horizon": {"type": "string"},
            "metric_family": {"type": "string"},
        },
        extra_constraints={
            "horizon": {"allowed_values": ["daily", "weekly", "monthly"]},
            "metric_family": {"allowed_values": ["dispatch", "delay", "mx_backlog"]},
        },
    ),
    "safety_knowledge_assistant": _spec(
        "safety_knowledge_assistant",
        ["knowledge", "vector_search", "memory"],
        extra_fields={
            "corpus": {"type": "string"},
            "question": {"type": "string"},
        },
        extra_constraints={
            "corpus": {"allowed_values": ["asrs", "sms", "sop"]},
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
