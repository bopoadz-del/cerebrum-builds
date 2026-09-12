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
    "estate_registry": _spec("estate_registry", ["database", "storage", "validation"]),
    "estate_maintenance": _spec("estate_maintenance", []),
    "evidence_verifier": _spec("evidence_verifier", []),
    "readiness_engine": _spec("readiness_engine", []),
    "portfolio_rollup": _spec("portfolio_rollup", []),
    "house_manual_sop": _spec(
        "house_manual_sop", ["document_engine", "knowledge", "vector_search"]
    ),
    "vendor_budget": _spec(
        "vendor_budget", ["formula_executor", "audit", "notification"]
    ),
    "preventive_maintenance": _spec(
        "preventive_maintenance", ["workflow", "event_bus", "queue"]
    ),
    "staff_scheduling": _spec("staff_scheduling", ["workflow", "team", "notification"]),
    "principal_dashboard": _spec("principal_dashboard", ["dashboard", "analytics"]),
    "property_onboarding": _spec(
        "property_onboarding", ["spec_analyzer", "recommendation_template"]
    ),
    "dual_rag_sop": _spec(
        "dual_rag_sop", ["knowledge", "vector_search", "document_engine"]
    ),
    "dual_rag_estate_docs": _spec(
        "dual_rag_estate_docs", ["knowledge", "vector_search", "document_engine"]
    ),
    "composed_ops_loop": _spec("composed_ops_loop", []),
    "evidence_capture": _spec("evidence_capture", ["capture"]),
    "human_authority_gate": _spec("human_authority_gate", []),
}

CAPABILITIES = SPECS
REQUIRED_CAPABILITY_IDS = tuple(SPECS.keys())


def get_spec(capability_id: str) -> Dict[str, Any]:
    try:
        return SPECS[capability_id]
    except KeyError as exc:
        raise KeyError(f"unknown capability: {capability_id}") from exc
