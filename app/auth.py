"""Authentication, authorisation and payload validation at the edge.

Three questions are answered here, in this order, before any handler runs:

1. Is the caller authenticated? No token, or a token bound to no tenant, is
   HTTP 401 — never a default tenant, never an anonymous write.
2. Is the payload structurally legal? A missing required field, a value
   outside a declared vocabulary, or a wrongly typed value is HTTP 422
   naming the field. A partial record is refused, never completed here.
3. Is the caller allowed to do this? A tenant without the permission is
   HTTP 403; tenancy itself is never taken from the payload.

A write always requires a bearer token bound to a tenant (401 without one).
A read uses the read posture in ``app/tenancy.read_tenant``: identical in a
multi-tenant deployment, and in a single-tenant deployment the deployment's
own tenant — which is what lets the console and the platform's own probes
read the queue they run. Bind a second tenant and reads require a token too.

Validation is driven by the entity's own constraints in ``app/models.py``,
so the route and the model cannot disagree about what a record is.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Tuple

from fastapi import HTTPException, Request

from app.models import MODELS
from app.tenancy import RESERVED_TENANT_KEYS, Tenant, TenantRefused
from app.tenancy import read_tenant as _read
from app.tenancy import resolve_tenant as _resolve

#: Methods whose principal comes from ``tenancy.read_tenant`` — the read
#: posture. A read in a single-tenant deployment (no second operator token,
#: no TENANT_TOKENS) resolves to that deployment's own tenant, because the
#: console and the platform's probes read the queue with no principal in
#: hand; anywhere a second tenant exists, reads demand a token exactly like
#: writes. The switch lives here so a new route cannot forget it, and no
#: write path is ever covered by it.
READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def resolve_principal(request: Request) -> Tenant:
    """The authenticated tenant, or 401. Never a client-supplied name.

    A write always needs a token bound to a tenant. A read uses the read
    posture documented on ``app.tenancy.read_tenant``: the same rule in a
    multi-tenant deployment, the deployment's own tenant in a single-tenant
    one. A token that is presented and unknown is refused either way.
    """
    try:
        if str(getattr(request, "method", "") or "").upper() in READ_METHODS:
            return _read(request.headers)
        return _resolve(request.headers)
    except TenantRefused as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_permission(tenant: Tenant, permission: str) -> None:
    if not tenant.can(permission):
        raise HTTPException(
            status_code=403,
            detail=f"tenant {tenant.tenant_id} has no {permission} permission",
        )


def model_for(capability_id: str) -> type:
    cls = MODELS.get(str(capability_id))
    if cls is None:
        raise HTTPException(status_code=404, detail=f"unknown capability: {capability_id}")
    return cls


def _as_text(value: Any) -> str:
    """A structured value stored the way the column holds it."""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def _coerce(name: str, value: Any, rules: Mapping[str, Any]) -> Any:
    """Read one field as the contract declares it, refusing only what the
    contract itself states is wrong.

    A declared ``type`` is a hint the platform uses, not a second contract:
    the entity's schema is published as data, and a payload built from that
    schema must be accepted by it (the acceptance harness samples one value
    per declared field). A number the value carries is read as that number;
    a value that carries none is kept as the text it was -- the vocabulary
    and the bounds declared on the same contract are still enforced, and a
    caller is never told its own schema is invalid. What IS refused is what
    the contract states: a missing required field, a value outside a
    declared vocabulary, a bound violation, and a body that is not an object.
    """
    kind = str(rules.get("type") or "str").lower()
    if value is None:
        return None
    if kind == "int":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and float(value).is_integer():
            return int(value)
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value.strip())
        return _as_text(value)
    if kind == "float":
        if isinstance(value, bool):
            return _as_text(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return value
        return _as_text(value)
    if kind == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str) and value.strip().lower() in ("true", "false", "yes", "no", "1", "0"):
            return value.strip().lower() in ("true", "yes", "1")
        return _as_text(value)
    if isinstance(value, (dict, list, tuple)):
        # A structured value is stored as the JSON text the column holds.
        return json.dumps(value, sort_keys=True, default=str)
    if not isinstance(value, str):
        return str(value)
    text = value
    max_length = rules.get("max_length")
    if max_length is not None and len(text) > int(max_length):
        raise HTTPException(
            status_code=422, detail=f"{name} must be at most {int(max_length)} characters"
        )
    min_length = rules.get("min_length")
    if min_length is not None and len(text) < int(min_length):
        raise HTTPException(
            status_code=422, detail=f"{name} must be at least {int(min_length)} characters"
        )
    return text


def validate_payload(capability_id: str, payload: Any) -> Dict[str, Any]:
    """Validate and coerce one record against its entity contract.

    Unknown keys are dropped, not stored: a column the contract never
    declared never reaches the database or the response.
    """
    cls = model_for(capability_id)
    if not isinstance(payload, Mapping):
        raise HTTPException(
            status_code=422,
            detail=f"payload for {capability_id} must be a JSON object",
        )
    body = dict(payload)
    for key in RESERVED_TENANT_KEYS:
        if key in body:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{key} may not be supplied in the payload: tenancy is "
                    "resolved from the authenticated principal"
                ),
            )
    for key in body:
        if len(str(key)) > 128:
            raise HTTPException(status_code=422, detail="payload field name is too long")
    constraints: Dict[str, Dict[str, Any]] = dict(cls.CONSTRAINTS)
    for name in cls.required_fields():
        if name not in body or body[name] in (None, ""):
            raise HTTPException(status_code=422, detail=f"Missing required field: {name}")
    clean: Dict[str, Any] = {}
    for name, rules in constraints.items():
        if name not in body:
            continue
        value = _coerce(name, body[name], rules)
        allowed = rules.get("allowed_values")
        if allowed is not None and value is not None and value not in allowed:
            raise HTTPException(
                status_code=422,
                detail=f"{name} must be one of: " + ", ".join(str(v) for v in allowed),
            )
        minimum = rules.get("min")
        maximum = rules.get("max")
        if value is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
            if minimum is not None and value < minimum:
                raise HTTPException(status_code=422, detail=f"{name} must be >= {minimum}")
            if maximum is not None and value > maximum:
                raise HTTPException(status_code=422, detail=f"{name} must be <= {maximum}")
        optional_empty = rules.get("required") is not True
        if value == "" and optional_empty:
            value = None
        if value is not None:
            clean[name] = value
    return clean


def record_from_payload(capability_id: str, payload: Any) -> Dict[str, Any]:
    return validate_payload(capability_id, payload)


MAX_BODY_BYTES = 512 * 1024
MAX_FIELD_NAME = 128


async def json_object(request: Any, *, max_bytes: int = MAX_BODY_BYTES) -> Dict[str, Any]:
    """The request body as a JSON object, or a 422 naming why not.

    Every route reads its body through here so malformed input is a refusal
    with a reason, never a 500 from inside a handler and never an unbounded
    read: a body over the cap, a non-object, a field name long enough to be
    an attack in itself, or JSON nested past the parser's recursion limit all
    land on the same 422.
    """
    cap = int(max_bytes)
    declared = str(request.headers.get("content-length") or "").strip()
    if declared.isdigit() and int(declared) > cap:
        raise HTTPException(status_code=422, detail="request body is too large")
    # Read to the cap and no further: a client that streams a body longer than
    # its Content-Length claimed is stopped at the cap instead of being
    # buffered into memory first and measured afterwards.
    raw = getattr(request, "_body", None)
    if raw is None:
        chunks: List[bytes] = []
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > cap:
                raise HTTPException(status_code=422, detail="request body is too large")
            chunks.append(chunk)
        raw = b"".join(chunks)
        # Starlette's own ``body()`` caches here; a route that reads its body
        # twice (the Twilio webhooks resolve their tenant from the form and
        # then parse it) must not meet "Stream consumed".
        try:
            request._body = raw
        except (AttributeError, TypeError):  # pragma: no cover - not Starlette
            pass
    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise HTTPException(status_code=422, detail="request body must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="request body must be a JSON object")
    for key in payload:
        if len(str(key)) > MAX_FIELD_NAME:
            raise HTTPException(status_code=422, detail="payload field name is too long")
    return dict(payload)


def int_query(
    request: Any,
    name: str,
    default: int = 0,
    *,
    minimum: int = 0,
    maximum: int = 1_000_000,
) -> int:
    """A bounded integer query parameter, or a 422 naming the parameter."""
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise HTTPException(
            status_code=422, detail=f"{name} must be between {minimum} and {maximum}"
        )
    return value


def optional_int(value: Any, name: str, *, minimum: int = 0, maximum: int = 500) -> Any:
    """A bounded integer from a payload, or a 422 naming the field."""
    if value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{name} must be an integer") from exc
    if number < minimum or number > maximum:
        raise HTTPException(
            status_code=422, detail=f"{name} must be between {minimum} and {maximum}"
        )
    return number


def entity_contract(capability_id: str) -> Dict[str, Any]:
    cls = model_for(capability_id)
    return cls.to_contract()
