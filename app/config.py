"""Settings for CallOps: read once, named, and never invented.

Every operator-owned value lives here. Two rules this module exists to keep:

* A credential the operator supplies is read with ``os.environ.get`` and has
  no baked default that would let the platform act as if it were configured.
  Where an operation cannot proceed without it, the operation refuses by
  name (``BusinessSettingMissing``) instead of guessing a country, a
  currency or a tax rate the brief never stated.
* A value with an operational default (a call cap, a window) is still a
  named setting the operator can change, documented in README.md.

``APP_ENV=production`` additionally refuses boot when a secret is missing
(see :func:`validate_boot`), so a misconfigured deploy fails with the
variable's own name instead of at 3am inside a request.
"""

from __future__ import annotations

import os
from typing import List, Optional

#: Country, currency and tax are NOT stated by the brief. No default is
#: invented for any of them; the money paths refuse and name the setting.
UNSET_BY_BRIEF: tuple[str, ...] = (
    "CURRENCY",
    "VAT_RATE",
    "BROKER_COMMISSION_RATE",
)


class SettingMissing(RuntimeError):
    """A setting the operator must supply was read and is not there."""

    def __init__(self, name: str, purpose: str) -> None:
        self.name = name
        self.purpose = purpose
        super().__init__(
            f"{name} is not set and CallOps will not invent it "
            f"({purpose}). Set {name} in the environment before using this path."
        )


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    raw = os.environ.get(name)
    if raw is None:
        return default
    raw = raw.strip()
    return raw if raw else default


def require_text(name: str, purpose: str) -> str:
    """A setting with no defensible default: present, or named in the error."""
    value = env(name)
    if not value:
        raise SettingMissing(name, purpose)
    return value


def require_float(name: str, purpose: str) -> float:
    value = require_text(name, purpose)
    try:
        return float(str(value).rstrip("%"))
    except ValueError as exc:
        raise SettingMissing(name, purpose) from exc


def require_rate(name: str, purpose: str) -> float:
    """A rate the operator owns, accepted as ``0.05`` or ``5%``."""
    value = require_text(name, purpose)
    text = str(value).strip()
    try:
        if text.endswith("%"):
            return float(text[:-1]) / 100.0
        return float(text)
    except ValueError as exc:
        raise SettingMissing(name, purpose) from exc


def _int(name: str, default: int) -> int:
    raw = env(name)
    if raw is None:
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    raw = env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# -- product identity --------------------------------------------------------
APP_ENV = (env("APP_ENV", "development") or "development").lower()
PRODUCT_NAME = env("PRODUCT_NAME", "CallOps") or "CallOps"
PRODUCT_ID = env("PRODUCT_ID", "real-estate") or "real-estate"


def storage_path() -> str:
    return env("STORAGE_PATH", "./data") or "./data"


# -- money (no defaults: see UNSET_BY_BRIEF) ---------------------------------


def currency() -> str:
    return require_text("CURRENCY", "pricing, budgets and broker commission")


def vat_rate() -> float:
    return require_rate("VAT_RATE", "tax applied to a quoted price")


def broker_commission_rate() -> float:
    return require_rate("BROKER_COMMISSION_RATE", "commission owed on a closed deal")


#: Extra currency tokens the operator's project sheets use, for finding a
#: price sentence in a retrieved chunk: "AED,QAR" and so on. Empty by default
#: -- the brief states no country, so this platform names no currency of its
#: own; CURRENCY is added when the operator sets it, and nothing else is
#: assumed.
PRICE_CURRENCY_TOKENS: tuple = tuple(
    token.strip().upper()
    for token in (env("PRICE_CURRENCY_TOKENS") or "").split(",")
    if token.strip()
)


def money_settings_state() -> dict:
    """Whether each money setting is supplied — never its value.

    This is what the console shows and what ``GET /v1/settings`` returns: a
    setting's *presence* is a fact an operator may see; its value is
    configuration that does not belong in an API response.
    """
    state = {name: bool(env(name)) for name in UNSET_BY_BRIEF}
    state["configured"] = all(state.values())
    return state


# -- dialling policy (operator-owned, with stated defaults) -------------------
MAX_ATTEMPTS = _int("MAX_ATTEMPTS", 3)                 # brief: max 3 attempts
RETRY_BACKOFF_MINUTES = _int("RETRY_BACKOFF_MINUTES", 45)
RETRY_BACKOFF_FACTOR = _float("RETRY_BACKOFF_FACTOR", 2.0)
DAILY_CALL_CAP = _int("DAILY_CALL_CAP", 250)
CONCURRENCY = _int("CONCURRENCY", 3)
DIAL_INTERVAL_SECONDS = _int("DIAL_INTERVAL_SECONDS", 30)
CALL_WINDOW_START = env("CALL_WINDOW_START", "09:00") or "09:00"
CALL_WINDOW_END = env("CALL_WINDOW_END", "20:00") or "20:00"
#: Per-language best windows: "HH:MM-HH:MM;HH:MM-HH:MM" in CALL_WINDOW_TZ.
CALL_WINDOW_BY_LANGUAGE = {
    "en": env("CALL_WINDOW_EN", "10:00-12:30;17:00-20:00") or "10:00-12:30;17:00-20:00",
    "ar": env("CALL_WINDOW_AR", "11:00-13:30;19:00-22:00") or "11:00-13:30;19:00-22:00",
}
CALL_WINDOW_TZ = env("CALL_WINDOW_TZ", "UTC") or "UTC"
CALL_WINDOW_DAYS = env("CALL_WINDOW_DAYS", "mon,tue,wed,thu,fri,sat") or "mon,tue,wed,thu,fri,sat"


# -- voice edge (stubbed until the operator connects an account) -------------
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_CALLER_NUMBER = env("TWILIO_CALLER_NUMBER")
TWILIO_API_BASE = env("TWILIO_API_BASE", "https://api.twilio.com/2010-04-01") or ""
TWILIO_ASR_LANGUAGE = {"en": "en-US", "ar": "ar-SA"}
TWILIO_TTS_VOICE = {
    "en": env("TWILIO_VOICE_EN", "Polly.Joanna-Neural") or "Polly.Joanna-Neural",
    "ar": env("TWILIO_VOICE_AR", "Polly.Hala-Neural") or "Polly.Hala-Neural",
}
BROKER_TRANSFER_NUMBER = env("BROKER_TRANSFER_NUMBER")
#: Where the carrier fetches TwiML and posts status callbacks. Settings, not
#: request fields: a caller who could name them could point the carrier at
#: anything on the operator's account.
TWILIO_ANSWER_URL = env("TWILIO_ANSWER_URL")
TWILIO_STATUS_CALLBACK_URL = env("TWILIO_STATUS_CALLBACK_URL")
CONFERENCE_BRIDGE_TIMEOUT_SECONDS = _int("CONFERENCE_BRIDGE_TIMEOUT_SECONDS", 45)


def voice_state() -> dict:
    """Whether the Twilio edge is connected. Absent credentials are honest."""
    missing: List[str] = [
        name
        for name, value in (
            ("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID),
            ("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN),
            ("TWILIO_CALLER_NUMBER", TWILIO_CALLER_NUMBER),
        )
        if not value
    ]
    return {
        "connected": not missing,
        "missing": missing,
        "caller_number": TWILIO_CALLER_NUMBER,
        "stub": bool(missing),
    }


# -- connectors --------------------------------------------------------------
SALES_CHANNEL_WEBHOOK = env("SALES_CHANNEL_WEBHOOK") or env("NOTIFY_WEBHOOK_URL")
BROKER_ALERT_WEBHOOK = env("BROKER_ALERT_WEBHOOK") or SALES_CHANNEL_WEBHOOK
CREDITOR_WEBHOOK_TIMEOUT_SECONDS = _int("WEBHOOK_TIMEOUT_SECONDS", 8)
#: Egress is refused unless the host is public or named here. A platform that
#: posts to whatever URL a payload names is a request-forgery proxy.
EGRESS_ALLOWLIST = tuple(
    host.strip()
    for host in (env("EGRESS_ALLOWLIST", "") or "").split(",")
    if host.strip()
)
CRM_DESTINATION = env("CRM_DESTINATION")
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = env("GOOGLE_REFRESH_TOKEN")
GOOGLE_DRIVE_FOLDER_ID = env("GOOGLE_DRIVE_FOLDER_ID")
LOCAL_DRIVE_ROOT = env("LOCAL_DRIVE_ROOT")
MCP_TOOL_SCOPE = env("MCP_TOOL_SCOPE", "platform") or "platform"


# -- conversation / retrieval ------------------------------------------------
LLM_PROVIDER = env("LLM_PROVIDER")
LLM_API_KEY = env("LLM_API_KEY")
LLM_MODEL = env("LLM_MODEL", "deterministic-planner") or "deterministic-planner"
LLM_BASE_URL = env("LLM_BASE_URL", "https://api.openai.com/v1") or ""
RETRIEVAL_TOP_K = _int("RETRIEVAL_TOP_K", 4)
RETRIEVAL_MIN_SCORE = _float("RETRIEVAL_MIN_SCORE", 0.05)
CHUNK_CHARACTERS = _int("CHUNK_CHARACTERS", 900)
CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 120)


# -- auth --------------------------------------------------------------------
PLATFORM_TOKEN = env("PLATFORM_TOKEN", "dev-local-token") or "dev-local-token"
PLATFORM_TOKEN_B = env("PLATFORM_TOKEN_B", "dev-local-token-b") or "dev-local-token-b"


def validate_boot() -> List[str]:
    """Refuse a production boot that is missing a secret, naming it.

    Development keeps the documented dev defaults so a laptop and the test
    suite can boot; production must be told what it is.
    """
    problems: List[str] = []
    if APP_ENV in ("production", "prod", "staging"):
        for name, value in (
            ("PLATFORM_TOKEN", env("PLATFORM_TOKEN")),
            ("PLATFORM_TOKEN_B", env("PLATFORM_TOKEN_B", PLATFORM_TOKEN_B)),
        ):
            if not value or value in ("dev-local-token", "dev-local-token-b"):
                problems.append(
                    f"{name} is unset or still the development default in "
                    f"APP_ENV={APP_ENV}; set it before serving traffic"
                )
    if problems:
        raise SettingMissing(problems[0].split(" ")[0], "; ".join(problems))
    return problems
