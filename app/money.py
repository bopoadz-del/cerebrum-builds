"""Money settings for this platform: the United Arab Emirates, AED.

The brief fixes the country (United Arab Emirates) and the currency (AED, the
UAE Dirham), so those are constants and every amount the platform handles is
in AED.

It does **not** fix a tax rate. A UAE contractor's VAT position — the standard
rate, zero-rated exports, a reverse-charge import, or an exempt supply — is
theirs to configure, so every rate and term is a named setting read from the
environment with **no default value**. An unset setting is refused by name
(:class:`SettingMissing`) rather than guessed: this platform handles money, and
a silent 0% VAT on a payment application is a wrong valuation, not a default.

Set before use (no defaults are supplied):

    UAE_VAT_RATE_PERCENT         standard/recorded VAT rate, e.g. 5
    DEFAULT_RETENTION_PERCENT    contract retention, e.g. 5 or 10
    PAYMENT_TERM_DAYS            days from valuation to payment due

Read :func:`configured` to see which settings this deployment has been given.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

COUNTRY = "AE"
COUNTRY_NAME = "United Arab Emirates"
CURRENCY = "AED"
CURRENCY_NAME = "UAE Dirham"
SUPPLY_TAX_NAME = "VAT"

#: name -> what a human needs to know to set it.
SETTINGS: Dict[str, str] = {
    "UAE_VAT_RATE_PERCENT": (
        "UAE VAT rate applied to a valuation, in percent (the contractor's own "
        "registration position decides the value)"
    ),
    "DEFAULT_RETENTION_PERCENT": (
        "retention withheld from a valuation where the contract does not name "
        "one, in percent"
    ),
    "PAYMENT_TERM_DAYS": (
        "days between a certified valuation and its payment due date"
    ),
}

#: Settings whose absence must never be papered over.
NO_DEFAULT = tuple(SETTINGS)


class SettingMissing(RuntimeError):
    """A money setting the operator must supply has not been set."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"{name} is not set. This platform does not guess a rate: set "
            f"{name} in the environment before it can value work "
            f"({SETTINGS.get(name, 'see app/money.py')})."
        )
        self.name = name


def setting(name: str) -> str:
    """Read a named setting, refusing by name when it is absent."""
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        raise SettingMissing(name)
    return str(raw).strip()


def number(name: str) -> float:
    """Read a numeric setting, refusing a non-numeric value by name."""
    raw = setting(name)
    try:
        return float(raw)
    except ValueError as exc:
        raise SettingMissing(f"{name} is not numeric: {raw!r}") from exc


def vat_rate_percent() -> float:
    return number("UAE_VAT_RATE_PERCENT")


def retention_rate_percent() -> float:
    return number("DEFAULT_RETENTION_PERCENT")


def payment_term_days() -> int:
    return int(number("PAYMENT_TERM_DAYS"))


def configured() -> Dict[str, Any]:
    """Which money settings this deployment has. Never invents a value."""
    return {
        "country": COUNTRY,
        "country_name": COUNTRY_NAME,
        "currency": CURRENCY,
        "currency_name": CURRENCY_NAME,
        "supply_tax": SUPPLY_TAX_NAME,
        "settings": {
            name: {
                "description": description,
                "set": bool(str(os.environ.get(name) or "").strip()),
                "value": os.environ.get(name) if str(os.environ.get(name) or "").strip() else None,
            }
            for name, description in SETTINGS.items()
        },
    }


def rate_from(record: Any, key: str, *, setting_name: str) -> float:
    """A rate carried by the record, else the deployment setting, else refuse."""
    if isinstance(record, dict):
        raw: Optional[Any] = record.get(key)
        if raw not in (None, ""):
            try:
                return float(raw)
            except (TypeError, ValueError) as exc:
                raise SettingMissing(f"{key} is not numeric: {raw!r}") from exc
    return number(setting_name)
