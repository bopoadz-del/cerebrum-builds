"""Secret handling and reserved-field hygiene for the platform.

Written by the factory WRITER role (codewhale exec)

Offline by construction: the only secret this product reads is its own
platform token, and it is never echoed back in a response, a log line, or
an error message.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Mapping

SECRET_KEYS = frozenset(
    {
        "token",
        "api_key",
        "apikey",
        "secret",
        "password",
        "passwd",
        "authorization",
        "smtp_pass",
        "sendgrid_api_key",
    }
)

#: Names the kernel treats as trust scope. A capability must never accept
#: them from a caller -- the tenant comes from the authenticated principal.
TRUST_SCOPE_KEYS = frozenset({"tenant_id", "organisation_id", "org_id", "project_id", "user_id"})

_RESERVED_ACTIONS = ("action",)

_SENSITIVE = re.compile(r"(?i)\b(bearer\s+)?[a-z0-9_\-]{24,}\b")


def redact(value: Any) -> Any:
    """Replace anything secret-shaped with a fixed marker."""
    if isinstance(value, Mapping):
        return {
            key: ("<redacted>" if str(key).lower() in SECRET_KEYS else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _SENSITIVE.sub("<redacted>", value)
    return value


def refuse_trust_scope(payload: Mapping[str, Any] | None) -> list:
    """Names of trust-scope fields a caller tried to supply."""
    data = payload if isinstance(payload, Mapping) else {}
    return sorted(key for key in data if str(key).lower() in TRUST_SCOPE_KEYS)


def refuse_reserved(payload: Mapping[str, Any] | None) -> list:
    """Names of dispatch-reserved fields that leaked into the payload."""
    data = payload if isinstance(payload, Mapping) else {}
    return sorted(key for key in data if str(key).lower() in _RESERVED_ACTIONS)


def strip_secrets(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Drop secret-shaped keys before a record is persisted."""
    return {
        key: value
        for key, value in (payload or {}).items()
        if str(key).lower() not in SECRET_KEYS
    }
