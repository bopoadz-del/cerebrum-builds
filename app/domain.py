"""Automotive dealership kernel. Envelope-driven; no invented caller contracts."""

from __future__ import annotations

from typing import Any, Dict, Tuple

STATUS_VALUES = ("open", "in_progress", "closed")
STATUS_NEXT: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress",),
    "in_progress": ("closed",),
    "closed": (),
}

CONDITIONS = ("new", "used")
DESKS = ("sales", "finance", "service")
HORIZONS = ("today", "week", "month")

# Distinct listing scores — not a persist stub of 1.0.
INVENTORY_SCORE = {
    ("open", "new"): 0.45,
    ("open", "used"): 0.38,
    ("in_progress", "new"): 0.71,
    ("in_progress", "used"): 0.64,
    ("closed", "new"): 0.91,
    ("closed", "used"): 0.84,
}
DAYS_ON_LOT = {"open": 12, "in_progress": 4, "closed": 0}
INQUIRY_PRIORITY = {"open": "high", "in_progress": "normal", "closed": "low"}
ASK_PRICE = {"open": 28450.0, "in_progress": 27100.0, "closed": 25990.0}
LEAD_WEIGHT = {"today": 3, "week": 11, "month": 28}
DESK_HEADCOUNT = {"sales": 6, "finance": 2, "service": 4}


def envelope_status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def allowed_next_status(status: str) -> Tuple[str, ...]:
    return STATUS_NEXT.get(status, ())


def vehicle_condition(payload: Dict[str, Any]) -> str:
    condition = str(payload.get("condition") or "new")
    return condition if condition in CONDITIONS else "new"


def inventory_score(status: str, condition: str = "new") -> float:
    return INVENTORY_SCORE.get((status, condition), INVENTORY_SCORE[("open", "new")])


def days_on_lot(status: str) -> int:
    return DAYS_ON_LOT.get(status, DAYS_ON_LOT["open"])


def inquiry_priority(status: str) -> str:
    return INQUIRY_PRIORITY.get(status, "high")


def ask_price(status: str) -> float:
    return ASK_PRICE.get(status, ASK_PRICE["open"])


def lead_count(horizon: str) -> int:
    return LEAD_WEIGHT.get(horizon, LEAD_WEIGHT["today"])


def desk_name(payload: Dict[str, Any]) -> str:
    desk = str(payload.get("desk") or "sales")
    return desk if desk in DESKS else "sales"


def desk_headcount(desk: str) -> int:
    return DESK_HEADCOUNT.get(desk, DESK_HEADCOUNT["sales"])


def board_horizon(payload: Dict[str, Any]) -> str:
    horizon = str(payload.get("horizon") or "today")
    return horizon if horizon in HORIZONS else "today"
