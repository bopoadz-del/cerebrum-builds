"""aviation_core — GENERATE. Riyadh Air RX kernel: network, hub, portfolio framing."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids; booking-engine seats/PNRs

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
STATUS_NEXT: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress",),
    "in_progress": ("closed",),
    "closed": (),
}

RX_HUB = "RUH"
RX_HQ = "Riyadh"
RX_CARRIER = "RX"
NETWORK_FLOOR = 100
PORTFOLIO_FRAMING = "airline_ops_portfolio"


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _reference(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _carrier(payload: Dict[str, Any]) -> str:
    code = str(payload.get("carrier_code") or RX_CARRIER).strip().upper()
    return code if code else RX_CARRIER


def _hub_city(payload: Dict[str, Any]) -> str:
    city = str(payload.get("hub_city") or RX_HQ).strip()
    return city or RX_HQ


def _destination_count(payload: Dict[str, Any]) -> int:
    raw = payload.get("destination_count")
    if raw in (None, "", "sample"):
        return NETWORK_FLOOR
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return NETWORK_FLOOR
    return max(NETWORK_FLOOR, value)


def _network_coverage(destinations: int) -> Dict[str, Any]:
    gulf = min(18, destinations)
    europe = min(28, max(0, destinations - gulf))
    asia = min(24, max(0, destinations - gulf - europe))
    remainder = max(0, destinations - gulf - europe - asia)
    return {
        "destinations": destinations,
        "meets_hundred_plus": destinations >= NETWORK_FLOOR,
        "regions": {
            "gulf_and_ksa": gulf,
            "europe": europe,
            "asia": asia,
            "other": remainder,
        },
        "hub_iata": RX_HUB,
        "booking_engine": False,
    }


def _kernel(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = _status(payload)
    destinations = _destination_count(payload)
    return {
        "carrier_code": _carrier(payload),
        "legal_name": "Riyadh Air",
        "hq_city": _hub_city(payload),
        "hq_country": "SA",
        "digitally_native": True,
        "network": _network_coverage(destinations),
        "framing": PORTFOLIO_FRAMING,
        "not_a_booking_engine": True,
        "status": status,
        "allowed_next_status": list(STATUS_NEXT[status]),
        "reference": _reference(payload),
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Author the RX aviation kernel from the envelope. No Store blocks are bound."""
    record = {
        **payload,
        "status": _status(payload),
        "aviation_kernel": _kernel(payload),
    }
    return ok_envelope("aviation_core", record)
