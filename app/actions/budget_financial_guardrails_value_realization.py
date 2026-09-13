"""budget_financial_guardrails_value_realization — REUSE formula, analytics, audit."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql, notification.outbound
# NEVER: inventing unverified Store block ids

BLOCK_IDS = ["formula_executor", "analytics", "dashboard", "audit", "notification"]

STATUS_VALUES = ("open", "in_progress", "closed")
APPROVED_SAR = 12_500_000.0
APPROVED_FTE = 48.0
BURN_RATE = {"open": 0.08, "in_progress": 0.41, "closed": 0.97}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compute spend vs approved envelope and remaining delivery capacity."""
    status = str(payload.get("status") or "open")
    if status not in STATUS_VALUES:
        status = "open"
    currency = str(payload.get("currency") or "SAR")
    if currency not in {"SAR", "USD"}:
        currency = "SAR"
    burn = BURN_RATE[status]
    spent = round(APPROVED_SAR * burn, 2)
    remaining = round(APPROVED_SAR - spent, 2)
    fte_used = round(APPROVED_FTE * burn, 1)
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepare_block_input(block_id, payload),
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record = {
        **payload,
        "status": status,
        "oversight": {
            "budget_code": str(payload.get("budget_code") or payload.get("reference") or "sample"),
            "currency": currency,
            "approved": APPROVED_SAR,
            "spent": spent,
            "remaining": remaining,
            "within_envelope": remaining >= 0,
            "fte_approved": APPROVED_FTE,
            "fte_used": fte_used,
            "fte_remaining": round(APPROVED_FTE - fte_used, 1),
        },
    }
    return ok_envelope("budget_financial_guardrails_value_realization", record, blocks)
