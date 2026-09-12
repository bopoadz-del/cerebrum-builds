"""budget_capacity_oversight — GENERATE. Approved SAR envelope and FTE capacity."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
APPROVED_SAR = 12_500_000.0
APPROVED_FTE = 48.0
BURN_RATE = {"open": 0.08, "in_progress": 0.41, "closed": 0.97}


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _currency(payload: Dict[str, Any]) -> str:
    value = str(payload.get("currency") or "SAR")
    return value if value in {"SAR", "USD"} else "SAR"


def _money(value: float) -> float:
    return round(float(value), 2)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compute spend vs approved envelope and remaining delivery capacity."""
    status = _status(payload)
    burn = BURN_RATE[status]
    spent = _money(APPROVED_SAR * burn)
    remaining = _money(APPROVED_SAR - spent)
    fte_used = round(APPROVED_FTE * burn, 1)
    record = {
        **payload,
        "status": status,
        "oversight": {
            "budget_code": str(payload.get("budget_code") or payload.get("reference") or "sample"),
            "currency": _currency(payload),
            "approved": APPROVED_SAR,
            "spent": spent,
            "remaining": remaining,
            "within_envelope": remaining >= 0,
            "fte_approved": APPROVED_FTE,
            "fte_used": fte_used,
            "fte_remaining": round(APPROVED_FTE - fte_used, 1),
        },
    }
    return ok_envelope("budget_capacity_oversight", record)
