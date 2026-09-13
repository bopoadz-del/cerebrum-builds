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
    "transaction_capture": _spec(
        "transaction_capture",
        ["capture", "storage", "validation"],
        extra_fields={
            "account_name": {"type": "string"},
            "category": {"type": "string"},
            "amount": {"type": "number"},
        },
        extra_constraints={
            "category": {"allowed_values": ["income", "expense", "transfer"]},
            "amount": {"min": 1},
        },
    ),
    "financial_dashboard": _spec(
        "financial_dashboard",
        ["dashboard", "analytics"],
        extra_fields={
            "period": {"type": "string"},
            "currency": {"type": "string"},
        },
        extra_constraints={
            "period": {"allowed_values": ["month", "quarter", "year"]},
            "currency": {"allowed_values": ["USD", "EUR", "GBP"]},
        },
    ),
    "budgeting_and_alerts": _spec(
        "budgeting_and_alerts",
        ["formula_executor", "notification", "workflow"],
        extra_fields={
            "budget_name": {"type": "string"},
            "threshold_pct": {"type": "number"},
        },
        extra_constraints={
            "threshold_pct": {"min": 1},
        },
    ),
    "report_generation": _spec(
        "report_generation",
        ["document_engine", "recommendation_template"],
        extra_fields={
            "report_type": {"type": "string"},
            "period": {"type": "string"},
        },
        extra_constraints={
            "report_type": {"allowed_values": ["pnl", "expense_breakdown", "tax_summary"]},
            "period": {"allowed_values": ["month", "quarter", "year"]},
        },
    ),
    "audit_and_compliance": _spec(
        "audit_and_compliance",
        ["audit", "file_hasher"],
        extra_fields={
            "event_action": {"type": "string"},
            "evidence_label": {"type": "string"},
        },
        extra_constraints={
            "event_action": {"allowed_values": ["persist", "review", "export"]},
        },
    ),
    "data_synchronization": _spec(
        "data_synchronization",
        ["event_bus", "queue", "database"],
        extra_fields={
            "source_name": {"type": "string"},
            "sync_mode": {"type": "string"},
        },
        extra_constraints={
            "sync_mode": {"allowed_values": ["push", "pull", "bidirectional"]},
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
