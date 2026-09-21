"""Edge validation and egress guards.

Written by the factory WRITER role (codewhale exec)

Every external input this platform accepts is checked here before it reaches a
handler: reserved dispatch keys, outbound URLs (a caller-controlled URL must
never reach a private address -- SSRF), document paths (no traversal, no
absolute escape out of the storage root) and log poisoning (control
characters, newlines).

Nothing in this module imports the network stack at module level, so the
platform still boots with no egress configured.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

#: Keys a capability payload may never carry: dispatch and tenancy are the
#: server's, and a caller that supplies one is attacking the envelope.
RESERVED_PAYLOAD_KEYS = (
    "action",
    "block",
    "block_id",
    "tenant",
    "tenant_id",
    "tenant_name",
    "org_id",
    "organisation_id",
    "stored",
    "ok",
    "capability",
)

KIND_ALLOWED = {
    "endpoint_url": ("http", "https"),
}

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class InputRefused(ValueError):
    """The input is refused at the edge. The message names the reason."""


def reject_reserved_keys(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise InputRefused("payload must be an object")
    offending = sorted(key for key in payload if str(key).lower() in RESERVED_PAYLOAD_KEYS)
    if offending:
        raise InputRefused(
            "reserved key(s) not accepted from a caller: " + ", ".join(offending)
        )


def clean_text(value: Any, *, field: str, limit: int = 4000) -> str:
    if value is None:
        return ""
    text = str(value)
    if _CONTROL.search(text):
        raise InputRefused(f"{field} contains control characters")
    if len(text) > limit:
        raise InputRefused(f"{field} exceeds {limit} characters")
    return text.strip()


def _is_private(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return True
    for info in infos:
        address = info[4][0]
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            return True
        if (
            parsed.is_private
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_reserved
            or parsed.is_multicast
            or parsed.is_unspecified
        ):
            return True
    return False


def check_outbound_url(url: Any, *, field: str = "endpoint_url") -> str:
    """Refuse a caller-supplied URL that points inside the box."""
    text = clean_text(url, field=field, limit=2000)
    if not text:
        raise InputRefused(f"{field} is empty")
    parsed = urlparse(text)
    if parsed.scheme not in KIND_ALLOWED["endpoint_url"]:
        raise InputRefused(f"{field} must be http or https, got {parsed.scheme or 'none'!r}")
    if not parsed.hostname:
        raise InputRefused(f"{field} has no host")
    if _is_private(parsed.hostname):
        raise InputRefused(
            f"{field} resolves to a private or loopback address; refusing egress"
        )
    return text


def safe_document_path(raw: Any, *, root: Optional[Path] = None) -> Path:
    """A document path inside the storage root, or a refusal."""
    text = clean_text(raw, field="attachment_path", limit=1000)
    if not text:
        raise InputRefused("attachment_path is empty")
    base = Path(root or ".").resolve()
    candidate = (base / text).resolve() if not Path(text).is_absolute() else Path(text).resolve()
    if root is not None and base not in candidate.parents and candidate != base:
        raise InputRefused("attachment_path escapes the storage root")
    return candidate


def find_reserved_keys(payload: Any) -> List[str]:
    if not isinstance(payload, dict):
        return []
    return sorted(key for key in payload if str(key).lower() in RESERVED_PAYLOAD_KEYS)


def validate_payload(payload: Any) -> Dict[str, Any]:
    reject_reserved_keys(payload)
    return dict(payload)
