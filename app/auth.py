"""Fail-closed admin token check. Missing or unmatched secrets deny."""

from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

_SECRET_ENV = ("API_TOKEN", "CEREBRUM_API_TOKEN")


def configured_secret() -> str:
    for name in _SECRET_ENV:
        value = (os.environ.get(name) or "").strip()
        if value:
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


def require_admin_token(request: Request) -> str:
    """Deny unless a configured secret matches the caller token. Fail closed."""
    expected = configured_secret()
    token = presented_token(request)
    if not tokens_match(token, expected):
        raise HTTPException(status_code=401, detail="token required")
    return token
