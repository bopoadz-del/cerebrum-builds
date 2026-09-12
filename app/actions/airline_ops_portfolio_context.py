"""airline_ops_portfolio_context — GENERATE. RX ops framing, not a booking engine."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids; PNR/booking inventory

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
STATION_ROLE = {
    "RUH": "primary_hub",
    "JED": "west_gate",
    "DMM": "east_gate",
}
FRAMING_NOTE = {
    "portfolio": "technology_portfolio_context",
    "ops_context": "line_ops_context",
}


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _station(payload: Dict[str, Any]) -> str:
    value = str(payload.get("station") or "RUH")
    return value if value in STATION_ROLE else "RUH"


def _framing(payload: Dict[str, Any]) -> str:
    value = str(payload.get("framing") or "portfolio")
    return value if value in FRAMING_NOTE else "portfolio"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Attach airline-ops context for a portfolio item. Explicitly not a booking surface."""
    status = _status(payload)
    station = _station(payload)
    framing = _framing(payload)
    record = {
        **payload,
        "status": status,
        "ops_context": {
            "station": station,
            "station_role": STATION_ROLE[station],
            "hq": "Riyadh",
            "carrier": "RX",
            "framing": FRAMING_NOTE[framing],
            "booking_engine": False,
            "seats_inventory": False,
            "portfolio_only": True,
        },
    }
    return ok_envelope("airline_ops_portfolio_context", record)
