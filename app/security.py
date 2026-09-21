"""Guards between the outside world and the platform.

Four checks live here, each one a place the platform could otherwise be
turned against its own operator:

* ``check_egress`` — a private-address guard. The platform posts to
  webhooks, and a webhook URL that a caller (or a payload) controls is a
  request-forgery proxy pointed at the operator's own network. Public
  hosts, or hosts the operator explicitly allowlists, are reachable.
* ``safe_relative_path`` — path traversal guard for the local drive.
* ``reject_reserved`` — tenant/permission keys never travel in a payload.
* ``redact`` / ``mask_phone`` — nothing a credential looks like, and no
  full phone number, reaches a log line or an error body.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urlparse

from app import config
from app.tenancy import RESERVED_TENANT_KEYS, TenantRefused

#: Keys that would let a caller set its own authorisation.
RESERVED_CONTROL_KEYS = RESERVED_TENANT_KEYS + (
    "permissions",
    "roles",
    "capability_id",
    "id",
    "ok",
)

SECRET_KEY_RE = re.compile(r"(token|secret|password|api_key|authorization)", re.I)
PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{5,}\d")


class EgressRefused(RuntimeError):
    """A URL the platform will not dial: non-http, or a private address."""


#: RFC 6598 carrier-grade NAT: CPython 3.11 calls it neither private nor
#: reserved, so it needs naming here or it reads as a public host.
SHARED_ADDRESS_SPACE = ipaddress.ip_network("100.64.0.0/10")


def _is_public_ip(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        raw = info[4][0]
        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            return False
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
            or not address.is_global
            or (address.version == 4 and address in SHARED_ADDRESS_SPACE)
        ):
            # An allowlisted host is the operator's explicit exception; the
            # default is refusal, so a metadata endpoint (169.254.169.254)
            # named in a payload cannot be reached.
            if host in config.EGRESS_ALLOWLIST:
                return True
            return False
    return True


def check_egress(url: str) -> str:
    """Return the URL when it may be dialled, else raise ``EgressRefused``.

    The host is resolved here and the refusal is fail-closed on a resolution
    error. That leaves a resolve-then-connect gap a DNS answer could exploit:
    the guard decides on one answer and ``urllib`` connects on another. The
    mitigation available to this platform is the operator's own decision —
    ``EGRESS_ALLOWLIST`` names the hosts allowed to receive a delivery — and
    the gap is written down here rather than left as an assumption.
    """
    text = str(url or "").strip()
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise EgressRefused(f"scheme {parsed.scheme!r} is not http(s)")
    host = parsed.hostname or ""
    if not host:
        raise EgressRefused("no host in URL")
    if host in config.EGRESS_ALLOWLIST:
        return text
    if not _is_public_ip(host):
        raise EgressRefused(
            f"{host} resolves to a private, loopback or unresolvable address; "
            "add it to EGRESS_ALLOWLIST only if that is intended"
        )
    return text


def safe_relative_path(root: str, candidate: str) -> str:
    """Resolve ``candidate`` under ``root``, refusing traversal and absolutes."""
    from pathlib import Path

    raw = str(candidate or "").strip()
    if not raw:
        raise ValueError("path must be a non-empty relative path")
    if raw.startswith(("/", "\\")) or ".." in Path(raw).parts:
        raise ValueError("path must stay inside the drive root")
    base = Path(root).resolve()
    target = (base / raw).resolve()
    if base != target and base not in target.parents:
        raise ValueError("path escapes the drive root")
    return str(target)


def reject_reserved(payload: Mapping[str, Any] | None) -> None:
    if not isinstance(payload, Mapping):
        return
    for key in ("tenant", "tenant_id", "tenant_name", "org_id", "organisation_id"):
        if key in payload:
            raise TenantRefused(
                f"payload carries reserved tenancy key {key!r}; tenancy comes "
                "from the authenticated principal"
            )


def assert_no_payload_tenancy(payload: Mapping[str, Any] | None) -> None:
    reject_reserved(payload)


def redact(value: Any, *, limit: int = 200) -> Any:
    """Anything a credential could be is replaced before it is echoed/logged."""
    if isinstance(value, Mapping):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            if SECRET_KEY_RE.search(str(key)):
                out[str(key)] = "***redacted***"
            else:
                out[str(key)] = redact(item, limit=limit)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(item, limit=limit) for item in value]
    if isinstance(value, str):
        text = PHONE_RE.sub(lambda m: mask_phone(m.group(0)), value)
        return text[:limit]
    return value


def mask_phone(number: str) -> str:
    """Keep enough of a number to work with it, not enough to leak it."""
    digits = re.sub(r"\D", "", str(number or ""))
    if len(digits) <= 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]


def big_payload_keys(payload: Mapping[str, Any] | None, *, key_limit: int = 128) -> List[str]:
    """Field names no contract declares: absurd keys are a refused payload."""
    if not isinstance(payload, Mapping):
        return []
    return [str(k) for k in payload if len(str(k)) > key_limit]


def secret_values() -> Iterable[str]:
    """Every credential currently configured, for output scrubbing."""
    for name in (
        "PLATFORM_TOKEN",
        "PLATFORM_TOKEN_B",
        "TWILIO_AUTH_TOKEN",
        "LLM_API_KEY",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
    ):
        value = config.env(name)
        if value and len(value) > 5:
            yield value


def scrub(text: str) -> str:
    """Remove configured secrets from a string bound for a response or log."""
    out = str(text or "")
    for secret in secret_values():
        out = out.replace(secret, "***redacted***")
    return out
