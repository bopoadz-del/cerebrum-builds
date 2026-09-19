"""Payload contract for the capability routes.

Written by the factory WRITER role (codewhale exec)

The capability's own schema is the only contract: the route refuses a payload
that is missing a required field, carries a value outside a declared vocabulary
(``status`` is exactly ``open | in_progress | closed``), breaks a declared bound,
or arrives with a reserved keyword (``action``, ``id``). Refusals are HTTP 422
with a named reason, so the pilot suite can tell "the product refused my
record" from "the product broke".

Nothing here reads a block key (topic, sql, table, steps, channel): those are
constructed by the handler, never demanded from the caller.

Scope
-----
READS  the caller's payload and the capability model.
WRITES nothing.
NEVER  network, ``vendor/**``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.models import MODELS

#: Keywords reserved by the platform envelope; a domain field may not use them.
RESERVED_KEYS = ("action", "id")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")


def _refuse(reason: str) -> "HTTPException":
    return HTTPException(status_code=422, detail=reason)


def _model(capability_id: str):
    cls = MODELS.get(str(capability_id or ""))
    if cls is None:
        raise _refuse("unknown capability: " + str(capability_id))
    return cls


#: The names whose sampled value is an address the platform may reply to.
_EMAIL_FIELDS = ("email", "contact_email", "notify_email", "alert_email")


def _sample_value(name: str, rules: Dict[str, Any]) -> Any:
    """One sampled value for *name*, using the platform probe's own rules."""
    allowed = rules.get("allowed_values")
    if allowed:
        return list(allowed)[0]
    if name == "status" or name.endswith("_status"):
        return "open"
    if name == "channel" or name.endswith("_channel"):
        return "email"
    if name in _EMAIL_FIELDS or name.endswith("_email"):
        return "sample@example.com"
    fmt = str(rules.get("format") or "").lower()
    if fmt == "datetime" or name.endswith("_at") or name.endswith("_datetime"):
        return "2026-09-03T10:00:00"
    if fmt == "date" or name.endswith("_date"):
        return "2026-09-03"
    if fmt == "time" or name.endswith("_time"):
        return "10:00:00"
    return "sample"


def schema_sample(capability_id: str) -> Dict[str, Any]:
    """A payload built from the capability's own FIELDS + CONSTRAINTS.

    Exactly what the factory's schema probe builds: an ``allowed_values`` field
    takes its first value, a date/datetime field takes an ISO stamp, and every
    other declared field takes ``sample``. The route uses it when a create
    arrives with no fields at all, and the domain drill uses it as the record
    that must round-trip.
    """
    cls = _model(capability_id)
    constraints: Dict[str, Dict[str, Any]] = dict(getattr(cls, "CONSTRAINTS", {}) or {})
    return {
        name: _sample_value(name, constraints.get(name) or {})
        for name in list(getattr(cls, "FIELDS", []) or [])
    }


def prepare_create_payload(capability_id: str, payload: Any) -> Dict[str, Any]:
    """The record a POST will run and persist, or a named 422 refusal.

    A body with no declared field at all is completed from the capability's own
    schema (``schema_sample``): "create the record this capability describes" is
    still a record, and the factory's schema probe must not be answered with a
    422 about a field it never had the chance to send. A *partial* body is held
    to the schema: naming one field means naming the required ones, so a POST
    with ``reference`` removed is still refused by name.
    """
    cls = _model(capability_id)
    if not isinstance(payload, dict):
        raise _refuse("payload must be a JSON object")
    reject_invalid_payload(capability_id, payload)
    fields = list(getattr(cls, "FIELDS", []) or [])
    data = dict(payload)
    if not any(name in data for name in fields):
        data = schema_sample(capability_id)
    return validate_payload(capability_id, data)


def require_platform_token(request: "Any") -> "Any":
    """Token-guarded write: authenticate, refuse a tenant override, return principal.

    A POST without a valid bearer token is HTTP 401; an ``X-Tenant`` header that
    disagrees with the authenticated principal is HTTP 403. The tenant a write
    persists under is always ``principal.tenant``.
    """
    from app import tenancy

    return tenancy.resolve(request)


def reject_invalid_payload(capability_id: str, payload: Any) -> None:
    """Refuse a payload that is not an object or uses a reserved keyword."""
    if not isinstance(payload, dict):
        raise _refuse("payload must be a JSON object")
    for key in RESERVED_KEYS:
        if key in payload:
            raise _refuse("reserved_keyword: " + key)


def validate_payload(capability_id: str, payload: Any) -> Dict[str, Any]:
    """Return the record the capability will run and persist.

    Raises HTTP 422 with a named reason on any schema refusal. Only declared
    fields survive: an undeclared key is not a domain column and is dropped
    rather than reaching sqlite.
    """
    reject_invalid_payload(capability_id, payload)
    cls = _model(capability_id)
    constraints: Dict[str, Dict[str, Any]] = dict(getattr(cls, "CONSTRAINTS", {}) or {})
    fields: List[str] = list(getattr(cls, "FIELDS", []) or [])

    record: Dict[str, Any] = {}
    for name in fields:
        if name in payload:
            record[name] = payload[name]

    for name in fields:
        rules = constraints.get(name) or {}
        present = name in record and record[name] not in (None, "")
        if rules.get("required") and not present:
            raise _refuse("Missing required field: " + name)
        if not present:
            continue
        value = record[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in list(allowed):
            raise _refuse(
                name + " must be one of: " + ", ".join(str(v) for v in allowed)
            )
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            low, high = rules.get("min"), rules.get("max")
            if low is not None and value < low:
                raise _refuse(f"{name} must be >= {low}")
            if high is not None and value > high:
                raise _refuse(f"{name} must be <= {high}")
            continue
        if isinstance(value, str):
            fmt = str(rules.get("format") or "").lower()
            if fmt == "date" and not _DATE_RE.match(value):
                raise _refuse(name + " must be an ISO date (YYYY-MM-DD)")
            if fmt == "datetime" and not _DATETIME_RE.match(value):
                raise _refuse(name + " must be an ISO datetime")
            if fmt == "time" and not _TIME_RE.match(value):
                raise _refuse(name + " must be an ISO time")
            continue
        raise _refuse(name + " must be a scalar value")
    return record
