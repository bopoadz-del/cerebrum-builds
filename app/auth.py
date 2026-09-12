"""Fail-closed admin token check and CORS allowlist. Empty secret = deny."""

from __future__ import annotations

import hmac
import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request

_SECRET_ENV = ("API_TOKEN", "CEREBRUM_API_TOKEN")
CORS_ALLOWLIST_ENV = "CORS_ALLOWLIST"

# Reject empty and well-known placeholders. No git-default fallback.
_FORBIDDEN_SECRETS = frozenset(
    {
        "",
        "changeme",
        "change-me",
        "secret",
        "token",
        "password",
        "operator",
        "admin",
        "sample",
        "default",
        "test",
        "git-default",
        "placeholder",
        "x-api-token",
        "bearer",
        "authorization",
    }
)

_current_principal: ContextVar[Optional["Principal"]] = ContextVar(
    "current_principal", default=None
)


@dataclass(frozen=True)
class Principal:
    """Server-side identity bound from a matching operator/admin token."""

    subject: str
    role: str

    def as_dict(self) -> Dict[str, str]:
        return {"subject": self.subject, "role": self.role}


def configured_secret() -> str:
    for name in _SECRET_ENV:
        value = (os.environ.get(name) or "").strip()
        if value and value.lower() not in _FORBIDDEN_SECRETS:
            return value
    return ""


def presented_token(request: Request) -> str:
    raw = request.headers.get("authorization") or request.headers.get("x-api-token") or ""
    raw = raw.strip()
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    return raw


def tokens_match(presented: str, expected: str) -> bool:
    if not presented or not expected:
        return False
    presented_b = presented.encode("utf-8")
    expected_b = expected.encode("utf-8")
    if len(presented_b) != len(expected_b):
        hmac.compare_digest(expected_b, expected_b)
        return False
    return hmac.compare_digest(presented_b, expected_b)


def bind_principal(principal: Principal) -> Any:
    return _current_principal.set(principal)


def reset_principal() -> None:
    _current_principal.set(None)


def current_principal() -> Optional[Principal]:
    return _current_principal.get()


def require_principal() -> Principal:
    """Fail closed when no authenticated principal is bound. No silent drop."""
    principal = current_principal()
    if principal is None:
        raise RuntimeError("authenticated principal required")
    return principal


def require_admin_token(request: Request) -> Principal:
    """Deny unless a configured secret matches the caller token. Fail closed."""
    reset_principal()
    expected = configured_secret()
    token = presented_token(request)
    if not tokens_match(token, expected):
        raise HTTPException(status_code=401, detail="token required")
    # Shared bearer maps to a server-side operator/admin principal — never a
    # client-supplied actor. First matching env name wins (configured_secret).
    principal = Principal(subject="operator", role="admin")
    bind_principal(principal)
    return principal


def cors_allowlist() -> List[str]:
    """Env-driven origins. Empty default denies. Wildcard entries are dropped."""
    raw = (os.environ.get(CORS_ALLOWLIST_ENV) or "").strip()
    if not raw:
        return []
    origins: List[str] = []
    for part in raw.split(","):
        origin = part.strip()
        if not origin or origin == "*":
            continue
        origins.append(origin)
    return origins


class AllowlistCORSMiddleware:
    """Reflect only allowlisted Origins. Never '*'. Empty allowlist denies."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        header_map = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers") or []
        }
        origin = (header_map.get("origin") or "").strip()
        allowed = cors_allowlist()
        origin_ok = bool(origin) and origin != "*" and origin in allowed
        if scope.get("method") == "OPTIONS":
            headers = [(b"vary", b"Origin")]
            if origin_ok:
                headers.extend(
                    [
                        (b"access-control-allow-origin", origin.encode("latin-1")),
                        (b"access-control-allow-methods", b"GET, POST, OPTIONS"),
                        (
                            b"access-control-allow-headers",
                            b"Authorization, Content-Type, X-API-Token",
                        ),
                    ]
                )
            await send({"type": "http.response.start", "status": 200, "headers": headers})
            await send({"type": "http.response.body", "body": b""})
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((b"vary", b"Origin"))
                if origin_ok:
                    headers.append(
                        (b"access-control-allow-origin", origin.encode("latin-1"))
                    )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


def install_cors(app) -> None:
    """Install CORS from the allowlist. Wildcard origins are refused."""
    app.add_middleware(AllowlistCORSMiddleware)
