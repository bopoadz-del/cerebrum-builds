"""enterprise_portfolio_dashboard — GENERATE. Strategic initiative rollup for RX tech."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
HORIZON_WEIGHT = {"strategic": 3, "tactical": 2, "runway": 1}


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _horizon(payload: Dict[str, Any]) -> str:
    value = str(payload.get("horizon") or "strategic")
    return value if value in HORIZON_WEIGHT else "strategic"


def _initiative(payload: Dict[str, Any]) -> str:
    return str(payload.get("initiative_name") or payload.get("reference") or "sample")


def _score(status: str, horizon: str) -> int:
    status_pts = {"open": 20, "in_progress": 60, "closed": 100}[status]
    return status_pts + HORIZON_WEIGHT[horizon] * 10


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Roll a strategic initiative into the enterprise tech portfolio view."""
    status = _status(payload)
    horizon = _horizon(payload)
    record = {
        **payload,
        "status": status,
        "portfolio_card": {
            "initiative": _initiative(payload),
            "horizon": horizon,
            "owner_surface": "enterprise_and_corporate_technology",
            "health_score": _score(status, horizon),
            "tracks_value_realization": True,
            "not_a_booking_engine": True,
            "carrier": "RX",
        },
    }
    return ok_envelope("enterprise_portfolio_dashboard", record)
