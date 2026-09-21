"""Operational formulas for the hotel, over settings the operator owns.

Written by the factory WRITER role (codewhale exec)

COUNTRY, CURRENCY and TAX REGIME WERE NOT GIVEN in the brief, so this module
does not assume one. Currency and each tax rate are named settings read from
the environment with NO default:

    CURRENCY              ISO code the property bills in         (required)
    TAX_RATE_PERCENT      tax/VAT percentage on folio charges    (required)
    CITY_TAX_PER_NIGHT    flat per-night city/accommodation tax  (optional)

Until they are set, every financial RULE is refused by name -- the charge is
still recorded, because an operational record is not a tax calculation. The
thresholds used to segment guests are settings too, with stated defaults the
operator may override (a threshold is theirs, not ours).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


class SettingsError(RuntimeError):
    """A setting the operator must own was not supplied."""


def _env(name: str) -> Optional[str]:
    value = (os.environ.get(name) or "").strip()
    return value or None


def configured_currency() -> str:
    value = _env("CURRENCY")
    if not value:
        raise SettingsError(
            "CURRENCY is not set: the brief named no country or currency, so "
            "this platform will not choose one. Set CURRENCY (for example the "
            "ISO code your property bills in) before financial rules are used."
        )
    return value.upper()


def tax_rate_percent() -> float:
    raw = _env("TAX_RATE_PERCENT")
    if raw is None:
        raise SettingsError(
            "TAX_RATE_PERCENT is not set: no tax regime was named in the "
            "brief, so no rate is assumed. Set the property's tax/VAT "
            "percentage before tax is computed."
        )
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f"TAX_RATE_PERCENT={raw!r} is not a number") from exc
    if value < 0 or value > 100:
        raise SettingsError("TAX_RATE_PERCENT must be between 0 and 100")
    return value


def city_tax_per_night() -> float:
    raw = _env("CITY_TAX_PER_NIGHT")
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except ValueError as exc:
        raise SettingsError(f"CITY_TAX_PER_NIGHT={raw!r} is not a number") from exc


def money_settings_state() -> Dict[str, Any]:
    """What is configured, without raising: the honest report for a record."""
    state: Dict[str, Any] = {"configured": False, "settings": {}}
    try:
        state["settings"]["currency"] = configured_currency()
    except SettingsError as exc:
        state["missing_currency"] = str(exc)
    try:
        state["settings"]["tax_rate_percent"] = tax_rate_percent()
    except SettingsError as exc:
        state["missing_tax_rate_percent"] = str(exc)
    state["settings"]["city_tax_per_night"] = city_tax_per_night()
    state["configured"] = "currency" in state["settings"] and "tax_rate_percent" in state["settings"]
    return state


def folio_total(amount: Any, tax_rate: Optional[float] = None) -> Dict[str, Any]:
    """Charge plus tax, in the configured currency. Refuses without settings."""
    try:
        value = float(amount)
    except (TypeError, ValueError) as exc:
        raise SettingsError(f"amount {amount!r} is not a number") from exc
    if value < 0:
        raise SettingsError("amount must not be negative")
    currency = configured_currency()
    rate = tax_rate_percent() if tax_rate is None else float(tax_rate)
    if rate < 0 or rate > 100:
        raise SettingsError("tax rate must be between 0 and 100")
    tax = round(value * rate / 100.0, 2)
    return {
        "amount": round(value, 2),
        "tax_rate_percent": rate,
        "tax": tax,
        "total": round(value + tax, 2),
        "currency": currency,
    }


def occupancy_percent(rooms_sold: Any, total_rooms: Any) -> float:
    sold = float(rooms_sold or 0)
    total = float(total_rooms or 0)
    if total <= 0:
        raise SettingsError("total_rooms must be greater than zero")
    if sold < 0 or sold > total:
        raise SettingsError("rooms_sold must be between 0 and total_rooms")
    return round(100.0 * sold / total, 2)


def adr(room_revenue: Any, rooms_sold: Any) -> float:
    sold = float(rooms_sold or 0)
    if sold <= 0:
        raise SettingsError("rooms_sold must be greater than zero")
    return round(float(room_revenue or 0) / sold, 2)


def revpar(room_revenue: Any, total_rooms: Any) -> float:
    total = float(total_rooms or 0)
    if total <= 0:
        raise SettingsError("total_rooms must be greater than zero")
    return round(float(room_revenue or 0) / total, 2)


def _threshold(name: str, default: float) -> float:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise SettingsError(f"{name}={raw!r} is not a number") from exc


def rfm_thresholds() -> Dict[str, float]:
    return {
        "champion_monetary": _threshold("RFM_CHAMPION_MONETARY", 1000.0),
        "loyal_monetary": _threshold("RFM_LOYAL_MONETARY", 400.0),
        "potential_monetary": _threshold("RFM_POTENTIAL_MONETARY", 100.0),
        "recent_days": _threshold("RFM_RECENT_DAYS", 60.0),
        "lapsed_days": _threshold("RFM_LAPSED_DAYS", 365.0),
    }


def rfm_segment(recency_days: Any, frequency: Any, monetary: Any) -> Dict[str, Any]:
    """Segment from stay behaviour. Boundaries are inclusive on the line."""
    try:
        recency = float(recency_days)
        freq = float(frequency)
        value = float(monetary)
    except (TypeError, ValueError) as exc:
        raise SettingsError("recency_days, frequency and monetary must be numeric") from exc
    if recency < 0 or freq < 0 or value < 0:
        raise SettingsError("recency_days, frequency and monetary must not be negative")
    limits = rfm_thresholds()
    if value > limits["champion_monetary"] and recency <= limits["recent_days"] and freq >= 3:
        segment = "champion"
    elif value > limits["loyal_monetary"] and recency <= limits["lapsed_days"]:
        segment = "loyal"
    elif value > limits["potential_monetary"]:
        segment = "potential"
    elif recency <= limits["lapsed_days"]:
        segment = "at_risk"
    else:
        segment = "dormant"
    return {
        "segment": segment,
        "r_score": 3 if recency <= limits["recent_days"] else (1 if recency > limits["lapsed_days"] else 2),
        "f_score": 3 if freq >= 3 else (1 if freq < 1 else 2),
        "m_score": 3 if value > limits["loyal_monetary"] else (1 if value <= limits["potential_monetary"] else 2),
        "thresholds": limits,
    }
