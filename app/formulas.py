"""Operational formulas for CallOps, over settings the operator owns.

Written by the factory WRITER role (codewhale exec)

COUNTRY, CURRENCY AND BROKER COMMISSION WERE NOT GIVEN in the brief, so this
module does not assume one. The money settings are read from the environment
with NO default and every rule that needs one is refused by name until it is
set:

    CURRENCY                  ISO code the brokerage prices in        (required)
    BROKER_COMMISSION_PERCENT commission on a closed deal, percent   (required)
    TAX_RATE_PERCENT          tax/VAT on a quoted price, percent     (optional)

The dialing numbers are arithmetic, not guesses: calls remaining today, the
spaced retry backoff for busy / no-answer / failed (max three attempts) and
the per-language best calling window. The caps themselves are the operator's
settings -- ``DAILY_CALL_CAP`` and ``CONCURRENCY`` -- with stated defaults
they may override, because a cap is theirs, not ours.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

#: Attempts a busy / no-answer / failed dial is allowed, and the spacing
#: between them (minutes). The third attempt spends the budget.
MAX_ATTEMPTS = 3
BACKOFF_MINUTES = (15, 60, 180)

#: Pacing settings the operator owns. Defaults are stated, not assumed.
DEFAULT_DAILY_CALL_CAP = 200
DEFAULT_CONCURRENCY = 3

#: Best calling window per language. Gulf residential calling peaks differ
#: from the English-speaking expatriate peak, so the window is per language
#: rather than one global setting.
BEST_CALL_WINDOWS = {
    "en": "10:00-12:00",
    "ar": "17:00-19:00",
}
DEFAULT_WINDOW = "09:00-18:00"


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
            "this platform will not choose one. Set CURRENCY (the ISO code "
            "the brokerage prices in) before a price or a commission is "
            "computed."
        )
    return value.upper()


def broker_commission_percent() -> float:
    raw = _env("BROKER_COMMISSION_PERCENT")
    if raw is None:
        raise SettingsError(
            "BROKER_COMMISSION_PERCENT is not set: no commission was named in "
            "the brief, so none is assumed. Set the brokerage's commission "
            "percentage before a commission is computed."
        )
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(
            f"BROKER_COMMISSION_PERCENT={raw!r} is not a number"
        ) from exc
    if value < 0 or value > 100:
        raise SettingsError("BROKER_COMMISSION_PERCENT must be between 0 and 100")
    return value


def tax_rate_percent() -> Optional[float]:
    raw = _env("TAX_RATE_PERCENT")
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f"TAX_RATE_PERCENT={raw!r} is not a number") from exc
    if value < 0 or value > 100:
        raise SettingsError("TAX_RATE_PERCENT must be between 0 and 100")
    return value


def money_settings_state() -> Dict[str, Any]:
    """Which money settings are present. /health and the console read this."""
    out: Dict[str, Any] = {}
    for name, fn in (
        ("CURRENCY", configured_currency),
        ("BROKER_COMMISSION_PERCENT", broker_commission_percent),
    ):
        try:
            out[name] = {"configured": True, "value": fn()}
        except SettingsError as exc:
            out[name] = {"configured": False, "error": str(exc)}
    try:
        out["TAX_RATE_PERCENT"] = {"configured": True, "value": tax_rate_percent()}
    except SettingsError as exc:
        out["TAX_RATE_PERCENT"] = {"configured": False, "error": str(exc)}
    return out


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def daily_call_cap(value: Any = None) -> int:
    return _positive_int(value if value is not None else _env("DAILY_CALL_CAP"),
                         DEFAULT_DAILY_CALL_CAP)


def concurrency(value: Any = None) -> int:
    parsed = _positive_int(value if value is not None else _env("CONCURRENCY"),
                           DEFAULT_CONCURRENCY)
    return max(1, parsed)


def retry_backoff_minutes(attempt: Any) -> int:
    """Minutes to wait before the next attempt. Attempt 1 -> first spacing."""
    index = max(1, _positive_int(attempt, 1)) - 1
    if index >= len(BACKOFF_MINUTES):
        return BACKOFF_MINUTES[-1]
    return BACKOFF_MINUTES[index]


def best_call_window(language: Any) -> str:
    key = str(language or "en").strip().lower()
    return BEST_CALL_WINDOWS.get(key, DEFAULT_WINDOW)


def dial_pacing(
    *,
    daily_call_cap: Any = None,
    attempts_today: Any = 0,
    attempt_count: Any = 0,
    language: Any = "en",
) -> Dict[str, Any]:
    """Calls remaining today, the retry spacing, and the window to dial in."""
    cap = globals()["daily_call_cap"](daily_call_cap)
    today = _positive_int(attempts_today, 0)
    attempts = _positive_int(attempt_count, 0)
    remaining = max(0, cap - today)
    exhausted = attempts >= MAX_ATTEMPTS
    return {
        "daily_call_cap": cap,
        "attempts_today": today,
        "calls_remaining": remaining,
        "concurrency": concurrency(),
        "attempt_count": attempts,
        "attempts_remaining": max(0, MAX_ATTEMPTS - attempts),
        "retry_backoff_minutes": 0 if exhausted else retry_backoff_minutes(attempts + 1),
        "next_attempt_allowed": not exhausted,
        "call_window": best_call_window(language),
        "language": str(language or "en").strip().lower(),
    }


def conversion_rate(attempted: Any, transferred: Any) -> float:
    """Transfers per attempted call, as a percentage rounded to 2 places."""
    tries = _positive_int(attempted, 0)
    if not tries:
        return 0.0
    return round((float(_positive_int(transferred, 0)) / float(tries)) * 100.0, 2)


def commission_amount(price: Any, rate_percent: Optional[float] = None) -> Dict[str, Any]:
    """Commission on a closed price, in the operator's configured currency.

    Refuses by name when CURRENCY or BROKER_COMMISSION_PERCENT is unset: the
    brief named neither, so inventing one would put a wrong number in front of
    a broker.
    """
    currency = configured_currency()
    rate = broker_commission_percent() if rate_percent is None else float(rate_percent)
    try:
        amount = float(price)
    except (TypeError, ValueError) as exc:
        raise SettingsError(f"price {price!r} is not a number") from exc
    if amount < 0:
        raise SettingsError("price must not be negative")
    commission = round(amount * rate / 100.0, 2)
    tax = tax_rate_percent()
    return {
        "currency": currency,
        "price": amount,
        "commission_percent": rate,
        "commission_amount": commission,
        "tax_rate_percent": tax,
        "total_with_tax": (
            round(amount * (1.0 + (tax or 0.0) / 100.0), 2) if tax is not None else None
        ),
    }
