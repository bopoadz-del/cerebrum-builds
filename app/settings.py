"""Operator settings, read once, with no invented values.

Written by the factory WRITER role (codewhale exec)

Country, currency and tax rates are the customer's values, not the
platform's. The brief for this build names none of them, so this module
declares each one as a named setting with **no default** and refuses to
render money until the operator supplies it. A platform that quietly picks a
currency produces invoices the customer cannot file.

Settings (all read from the environment at import):
    CURRENCY                  ISO 4217 code for money this platform prints
    TAX_VAT_RATE              VAT / GST rate as a decimal fraction (0.2 = 20%)
    TAX_SALES_TAX_RATE        sales-tax rate as a decimal fraction
    TAX_WITHHOLDING_RATE      withholding rate as a decimal fraction
    SMTP_HOST / SMTP_PORT / SMTP_FROM / SMTP_USERNAME / SMTP_PASSWORD
                              the mail relay for notification delivery

Undeclared means unset: :func:`money_settings` reports each one as ``None``
rather than guessing, and :func:`require` raises :class:`SettingMissing`
naming the variable. README.md lists every one of them as a value the
operator must set before use.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

#: Money and tax the brief did not name. No defaults, on purpose.
CURRENCY = "CURRENCY"
TAX_VAT_RATE = "TAX_VAT_RATE"
TAX_SALES_TAX_RATE = "TAX_SALES_TAX_RATE"
TAX_WITHHOLDING_RATE = "TAX_WITHHOLDING_RATE"

#: Delivery for the platform's one live connector (email).
SMTP_SETTINGS: Tuple[str, ...] = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_FROM",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
)

MONEY_SETTINGS: Tuple[str, ...] = (
    CURRENCY,
    TAX_VAT_RATE,
    TAX_SALES_TAX_RATE,
    TAX_WITHHOLDING_RATE,
)

REQUIRED_BEFORE_USE: Tuple[str, ...] = MONEY_SETTINGS


class SettingMissing(RuntimeError):
    """A value the customer owns was needed and never supplied."""


def raw(name: str) -> Optional[str]:
    """The setting as given, or None. Never a default."""
    value = (os.environ.get(name) or "").strip()
    return value or None


def require(name: str) -> str:
    value = raw(name)
    if value is None:
        raise SettingMissing(
            "%s is not set — the operator must supply this value before use"
            % name
        )
    return value


def currency() -> str:
    return require(CURRENCY)


def tax_rate(name: str) -> float:
    if name not in (TAX_VAT_RATE, TAX_SALES_TAX_RATE, TAX_WITHHOLDING_RATE):
        raise SettingMissing("unknown tax setting: %s" % name)
    value = require(name)
    try:
        return float(value)
    except ValueError:
        raise SettingMissing("%s must be a decimal rate, got %r" % (name, value)) from None


def money_or_none(amount: Any) -> Optional[Dict[str, Any]]:
    """An amount with its currency, or None when the operator set none.

    Returning None keeps the platform honest: a number without a currency is
    stored as a number, never printed as if it were money.
    """
    code = raw(CURRENCY)
    if code is None or amount in (None, ""):
        return None
    try:
        value = round(float(amount), 2)
    except (TypeError, ValueError):
        return None
    return {"amount": value, "currency": code}


def smtp_configured() -> bool:
    return raw("SMTP_HOST") is not None


def summary() -> Dict[str, Any]:
    """What the operator has set and what is still missing. No secrets."""
    return {
        "money": {name: raw(name) for name in MONEY_SETTINGS},
        "money_ready": all(raw(name) is not None for name in MONEY_SETTINGS),
        "smtp": {name: (name != "SMTP_PASSWORD" and raw(name)) or (raw(name) is not None)
                 for name in SMTP_SETTINGS},
        "smtp_configured": smtp_configured(),
        "required_before_use": list(REQUIRED_BEFORE_USE),
    }
