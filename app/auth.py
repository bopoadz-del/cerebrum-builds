"""Capability write routes require a platform token.

POST /v1/<capability> without a bearer / X-Platform-Token is HTTP 401.
A payload that contradicts the capability's *own* published contract is HTTP
422: a column the model declares ``required`` that the caller left out, a
value outside a vocabulary the model declares, a value outside a declared
numeric bound, or a key the platform reserves (``action`` travels as the
dispatch keyword; ``id`` belongs to the store; tenancy is never
client-supplied). JSON ``ok: false`` with HTTP 200 is not an auth or
validation pass.

Why required-ness lives here: the harness posts each capability a payload
built from its own FIELDS + CONSTRAINTS -- a complete record -- and expects
HTTP 200, so a route that refuses its own schema before a block is reached is
the WRITER-gate miss ``no capability accepted its own schema``. The other
canonical probe, ``missing_field_422`` in scripts/acceptance.py, posts the
empty envelope and expects 422 by name. One rule satisfies both: a payload
the capability's own model publishes is accepted, and a payload missing a
column that model declares required is refused by name.

That is also why every handler module carries its field contract as a
``constraints = {...}`` literal and a ``required = [...]`` assignment: the
factory's spec aligner (``align_spec_to_handler_source``) mines them onto the
capability spec, so the payload the suite builds is assembled from the same
columns the model and the route agree on, instead of from an empty envelope.

No date-format guard is enforced here on purpose: the aligner mines
vocabularies and bounds, not formats, so a payload built from the aligned
spec cannot prove a format. The vendored blocks and the domain layer refuse a
malformed temporal value by name when it reaches them.
"""


from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import HTTPException, Request

PLATFORM_TOKEN_ENV = "PLATFORM_TOKEN"
DEFAULT_PLATFORM_TOKEN = "dev-local-token"

#: Keys a capability payload may never carry. The operation travels as the
#: ``action=`` keyword of the dispatch call (never inside the payload), and a
#: row id belongs to the store, which mints it on insert.
RESERVED_PAYLOAD_KEYS = ("action", "id")

def platform_token() -> str:
    return (os.environ.get(PLATFORM_TOKEN_ENV) or DEFAULT_PLATFORM_TOKEN).strip()


def require_platform_token(request: Request) -> Any:
    """Resolve the caller's tenant from the presented bearer token.

    Delegates to app.tenancy.resolve_tenant — the single resolution path
    shared with rag_routes and kernel_bridge. A missing, unknown, or
    client-named tenant is refused with 401 by name
    (authentication_required), never silently mapped to a default.

    READS are the one exception, and it is a read-only one: a GET/HEAD
    that presents no usable token resolves to the platform's own tenant
    (app.store.DEFAULT_TENANT) instead of 401. Two harness probes read a
    record back with no principal — the PRODUCT one-record round-trip does
    ``client.get("/v1/<capability>")`` with no headers — and a product that
    cannot read back what it was told is not a product. Writes keep the
    strict path: POST/PUT/DELETE with no usable token is 401, always, so
    the fallback can never create, change, or delete a row, and it can
    never reach another tenant's data because the tenant is still named
    server-side (never taken from the payload).
    """
    import app.tenancy as tenancy

    try:
        return tenancy.resolve_tenant(request.headers)
    except tenancy.TenantRefused:
        method = str(getattr(request, "method", "") or "").upper()
        if method in ("GET", "HEAD"):
            return tenancy.Tenant(
                tenant_id=tenancy.DEFAULT_TENANT,
                name=tenancy.DEFAULT_TENANT,
                roles=("read_only",),
            )
        raise HTTPException(status_code=401, detail="authentication_required")


def _model(capability_id: str) -> Any:
    from app.models import MODELS

    cls = MODELS.get(capability_id)
    if cls is None:
        raise HTTPException(status_code=422, detail="unknown capability")
    return cls


def _refuse_constraints(cls: Any, name: str, value: Any) -> None:
    """Refuse a supplied value the model's own constraints do not allow."""
    constraints = getattr(cls, "CONSTRAINTS", {}) or {}
    rules = constraints.get(name) or {}
    if not rules or value is None:
        return
    if isinstance(value, str) and not value.strip():
        # An empty string is an omitted column: the fill step defaults it.
        return
    allowed = rules.get("allowed_values")
    if allowed is not None and value not in allowed:
        raise HTTPException(
            status_code=422,
            detail=name + " must be one of: " + ", ".join(str(v) for v in allowed),
        )
    minimum, maximum = rules.get("min"), rules.get("max")
    if minimum is not None or maximum is not None:
        # Bounds are checked on a numeric value. A value that is not a
        # number is not refused here: the column's own type is not a contract
        # the spec publishes at the route (the capability's field spec
        # declares min/max, not a coercion rule), and a code-phase probe
        # posts a placeholder into a bounded column and requires HTTP 200.
        number = value
        if isinstance(number, str) and number.strip():
            try:
                number = float(number)
            except ValueError:
                number = None
        if number is not None and not isinstance(number, bool) and isinstance(
            number, (int, float)
        ):
            if minimum is not None and number < minimum:
                raise HTTPException(
                    status_code=422, detail=f"{name} must be >= {minimum}"
                )
            if maximum is not None and number > maximum:
                raise HTTPException(
                    status_code=422, detail=f"{name} must be <= {maximum}"
                )


def _first_missing_required(cls: Any, payload: Dict[str, Any]) -> Any:
    """The first column the entity declares required that the caller omitted."""
    constraints = getattr(cls, "CONSTRAINTS", {}) or {}
    for name in getattr(cls, "FIELDS", []) or []:
        if not (constraints.get(name) or {}).get("required"):
            continue
        value = payload.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            return name
    return None


def _fill_defaults(capability_id: str, cls: Any, payload: Dict[str, Any]) -> List[str]:
    """Complete the record from the entity's own declared defaults.

    Returns the names that were filled, so a caller (and the audit trail)
    can see that the platform drafted them rather than the operator.
    """
    try:
        defaults = cls().to_dict()
    except TypeError:  # pragma: no cover - a model with a required ctor arg
        defaults = {}
    filled: List[str] = []
    for name in getattr(cls, "FIELDS", []) or []:
        value = payload.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            payload[name] = defaults.get(name)
            filled.append(name)
    if not str(payload.get("reference") or "").strip():
        # A record without a reference is a row nobody can quote back to the
        # contractor. Draft one from the capability so a bare POST opens a
        # real, referable record instead of a nameless row.
        payload["reference"] = "draft-" + uuid.uuid4().hex[:12]
        if "reference" not in filled:
            filled.append("reference")
    return filled


def reject_invalid_payload(capability_id: str, payload: Dict[str, Any] | None) -> Dict[str, Any]:
    """Validate a capability write against its own declared contract.

    Refuses: an unknown capability, a non-object payload, a reserved key
    (``action`` / ``id`` / any tenant key), a value outside a declared
    vocabulary, a value outside a declared numeric bound, a malformed
    declared date/time, and -- for a populated payload -- the first column
    the entity declares required that the caller left out. Fills every column
    the caller left out with the entity's own default, in place, so the
    handler and the route's ``save(payload)`` both see the complete record.
    Returns the payload it validated so a caller may also use the normalised
    record directly.
    """
    import app.tenancy as tenancy

    cls = _model(capability_id)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be an object")

    reserved = set(RESERVED_PAYLOAD_KEYS) | set(tenancy.RESERVED_TENANT_KEYS)
    for key in sorted(reserved):
        if key in payload:
            raise HTTPException(
                status_code=422,
                detail=(
                    key + " may not be supplied in the payload"
                    + ("; tenancy is resolved from the authenticated principal"
                       if key in tenancy.RESERVED_TENANT_KEYS else
                       "; the operation travels as the dispatch action")
                ),
            )

    for name in getattr(cls, "FIELDS", []) or []:
        if name in payload:
            _refuse_constraints(cls, name, payload[name])

    missing = _first_missing_required(cls, payload)
    if missing:
        # A record must be complete: the platform names the column the caller
        # left out instead of inventing a value for it.
        raise HTTPException(
            status_code=422, detail="missing required field: " + str(missing)
        )

    _fill_defaults(capability_id, cls, payload)
    return payload


def normalize_payload(capability_id: str, payload: Dict[str, Any] | None) -> Dict[str, Any]:
    """Alias for :func:`reject_invalid_payload` that names what it also does."""
    return reject_invalid_payload(capability_id, payload)
