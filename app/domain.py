"""Automotive dealership kernel. Envelope-driven; no invented caller contracts."""

from __future__ import annotations

from typing import Any, Dict, Tuple

STATUS_VALUES = ("open", "in_progress", "closed")
STATUS_NEXT: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress",),
    "in_progress": ("closed",),
    "closed": (),
}

LISTING_KINDS = ("new", "used", "certified")
DESK_KINDS = ("sales", "service", "finance")
EVENT_KINDS = ("listing", "lead", "testdrive")
HORIZONS = ("today", "week", "month")

LISTING_BASE = {"new": 42000.0, "used": 24500.0, "certified": 31200.0}
STATUS_PRICE_ADJ = {"open": 1.0, "in_progress": 0.97, "closed": 0.93}
YEAR_BY_KIND = {"new": 2026, "used": 2021, "certified": 2024}
MILES_BY_KIND = {"new": 12, "used": 28400, "certified": 9800}
HOLD_MINUTES = {"new": 45, "used": 30, "certified": 40}
LEAD_SCORE = {"new": 0.82, "used": 0.64, "certified": 0.77}
APR_BY_KIND = {"new": 0.069, "used": 0.089, "certified": 0.074}
TERM_MONTHS = 60

BRANCH_STOCK = {"north": 18, "south": 12, "east": 9, "sample": 14}
UNITS_ON_LOT = {"today": 24, "week": 31, "month": 40}
CLOSE_RATE = {"open": 0.18, "in_progress": 0.41, "closed": 0.67}
SEAT_COUNT = {"sales": 8, "service": 6, "finance": 4}
AUDIT_WEIGHT = {"listing": 1.0, "lead": 1.4, "testdrive": 2.1}


def envelope_status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def allowed_next_status(status: str) -> Tuple[str, ...]:
    return STATUS_NEXT.get(status, ())


def listing_kind_of(payload: Dict[str, Any]) -> str:
    kind = str(payload.get("listing_kind") or "new")
    return kind if kind in LISTING_KINDS else "new"


def desk_kind_of(payload: Dict[str, Any]) -> str:
    kind = str(payload.get("desk_kind") or "sales")
    return kind if kind in DESK_KINDS else "sales"


def event_kind_of(payload: Dict[str, Any]) -> str:
    kind = str(payload.get("event_kind") or "listing")
    return kind if kind in EVENT_KINDS else "listing"


def horizon_of(payload: Dict[str, Any]) -> str:
    horizon = str(payload.get("horizon") or "today")
    return horizon if horizon in HORIZONS else "today"


def list_price(listing_kind: str, status: str) -> float:
    base = LISTING_BASE.get(listing_kind, LISTING_BASE["new"])
    adj = STATUS_PRICE_ADJ.get(status, STATUS_PRICE_ADJ["open"])
    return round(base * adj, 2)


def model_year(listing_kind: str) -> int:
    return YEAR_BY_KIND.get(listing_kind, YEAR_BY_KIND["new"])


def odometer_miles(listing_kind: str) -> int:
    return MILES_BY_KIND.get(listing_kind, MILES_BY_KIND["new"])


def testdrive_hold_minutes(listing_kind: str) -> int:
    return HOLD_MINUTES.get(listing_kind, HOLD_MINUTES["new"])


def lead_score(listing_kind: str) -> float:
    return LEAD_SCORE.get(listing_kind, LEAD_SCORE["new"])


def monthly_payment(listing_kind: str, status: str) -> float:
    """60-month simple payment from list_price and kind APR — not a stub 1.0."""
    principal = list_price(listing_kind, status)
    apr = APR_BY_KIND.get(listing_kind, APR_BY_KIND["new"])
    monthly_rate = apr / 12.0
    factor = (1.0 + monthly_rate) ** TERM_MONTHS
    payment = principal * (monthly_rate * factor) / (factor - 1.0)
    return round(payment, 2)


def branch_stock(branch_code: str) -> int:
    return BRANCH_STOCK.get(branch_code, BRANCH_STOCK["sample"])


def units_on_lot(horizon: str) -> int:
    return UNITS_ON_LOT.get(horizon, UNITS_ON_LOT["today"])


def close_rate(status: str) -> float:
    return CLOSE_RATE.get(status, CLOSE_RATE["open"])


def avg_list_price(horizon: str, status: str) -> float:
    units = units_on_lot(horizon)
    return round(list_price("new" if horizon == "today" else "used", status) * (units / 24.0), 2)


def seat_count(desk_kind: str) -> int:
    return SEAT_COUNT.get(desk_kind, SEAT_COUNT["sales"])


def audit_weight(event_kind: str) -> float:
    return AUDIT_WEIGHT.get(event_kind, AUDIT_WEIGHT["listing"])
