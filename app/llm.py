"""Offline text composition for the platform's narrative fields.

HONESTY: the delivered platform performs **no** inference and makes **no**
network call. This module is a deterministic, rule-based composer: it turns a
capability record into the human-readable line a front-desk operator reads.
Anything a real model would be needed for is refused rather than faked, and
:func:`is_available` reports the truth so callers can branch.
"""

from __future__ import annotations

from typing import Any, Dict, List

MODEL_ID = "offline-template-composer.v1"
NETWORK = "disabled"


class LLMUnavailable(RuntimeError):
    """Raised when a caller asks for generation this platform cannot do."""


def is_available() -> bool:
    """False: this build has no model provider wired, by design."""
    return False


def composer_model() -> str:
    return MODEL_ID


def summarise(capability_id: str, record: Dict[str, Any]) -> str:
    """One deterministic line describing a capability record."""
    if not isinstance(record, dict):
        raise LLMUnavailable("summarise() needs a record mapping")
    subject = (
        record.get("patient_name")
        or record.get("owner_name")
        or record.get("report_name")
        or record.get("reference")
        or capability_id
    )
    parts: List[str] = [str(subject)]
    for key in (
        "species",
        "appointment_type",
        "vaccine_type",
        "diagnosis",
        "service_code",
        "metric_name",
        "reminder_type",
    ):
        value = record.get(key)
        if value:
            parts.append(f"{key.replace('_', ' ')}={value}")
    status = record.get("status")
    if status:
        parts.append(f"status={status}")
    return " | ".join(parts)


def compose_reminder(record: Dict[str, Any]) -> str:
    """Deterministic reminder body for one client communication record."""
    owner = str(record.get("owner_name") or "client").strip() or "client"
    reminder = str(record.get("reminder_type") or "follow_up").replace("_", " ")
    when = record.get("scheduled_for") or record.get("next_due_on") or "soon"
    body = str(record.get("message_body") or "").strip()
    if body:
        return body
    return f"Dear {owner}, this is your {reminder} notice for {when}."


def generate(prompt: str, **_kwargs: Any) -> str:
    """Refuse generation. No provider is configured in this build."""
    raise LLMUnavailable(
        "no model provider is configured in the delivered platform; "
        "use summarise() / compose_reminder() for deterministic text"
    )
