"""HTTP surface for the CallOps voice platform.

Kernel routes publish each build role's job. Capability routes run
entirely in-process: the caller's tenant is resolved from the bearer
token, the payload is validated against the capability's own model (422),
the handler dispatches to the vendored blocks, and only then is the request
persisted with the route's tenant-scoped ``save(payload)``. A cross-tenant
read answers 404: tenancy is resolved from the principal, never the payload.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app import jobs, store
from app.domain_ops import perform as perform_domain
from app.kernel_bridge import run_capability

router = APIRouter()


@router.get("/jobs")
def list_jobs() -> Dict[str, Any]:
    """Roster of every kernel job description."""
    return {"jobs": jobs.JOBS}


@router.get("/catalog")
def catalog() -> Dict[str, Any]:
    """COLLECTOR — Binding surveyor."""
    return jobs.CATALOG


@router.get("/inventory")
def inventory() -> Dict[str, Any]:
    """CLONER — Block stocker. Pinned vendor lock, read live."""
    return jobs.inventory()


@router.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    """WRITER — Platform manufacturer. Capability HTTP surface."""
    return {"items": jobs.CAPABILITIES}


@router.get("/gates")
def gates() -> Dict[str, Any]:
    """TESTER — Acceptance inspector. Coverage only; does not run tests."""
    return jobs.GATES


@router.get("/provenance")
def provenance() -> Dict[str, Any]:
    """STORE_MANAGER — Store registrar. Clone register and provenance."""
    return jobs.provenance()


# --- lead_intake_and_dial_queue ---


def _lead_intake_and_dial_queue_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.lead_intake_and_dial_queue import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _lead_intake_and_dial_queue_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'lead_name', 'phone', 'language', 'project_tag']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'lead_name': {'required': True}, 'phone': {'required': True}, 'language': {'allowed_values': ['en', 'ar'], 'required': True}, 'project_tag': {'required': True}, 'daily_call_cap': {'min': 1, 'max': 100000}, 'concurrency': {'min': 1, 'max': 50}, 'attempt_count': {'min': 0, 'max': 3}, 'retry_backoff_minutes': {'min': 0, 'max': 1440}, 'queue_status': {'allowed_values': ['queued', 'dialing', 'paused', 'exhausted']}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/lead_intake_and_dial_queue")
async def lead_intake_and_dial_queue_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("lead_intake_and_dial_queue", payload)
    _lead_intake_and_dial_queue_edge_guard(payload)
    CAPABILITY_ID = "lead_intake_and_dial_queue"
    handle = _lead_intake_and_dial_queue_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("lead_intake_and_dial_queue", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/lead_intake_and_dial_queue")
def lead_intake_and_dial_queue_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["lead_intake_and_dial_queue"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("lead_intake_and_dial_queue", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/lead_intake_and_dial_queue/{item_id}")
def lead_intake_and_dial_queue_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("lead_intake_and_dial_queue", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/lead_intake_and_dial_queue/{item_id}")
async def lead_intake_and_dial_queue_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "lead_intake_and_dial_queue", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "lead_intake_and_dial_queue", "result": result}


@router.delete("/lead_intake_and_dial_queue/{item_id}")
async def lead_intake_and_dial_queue_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "lead_intake_and_dial_queue", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "lead_intake_and_dial_queue", "result": result}


# --- call_state_machine ---


def _call_state_machine_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.call_state_machine import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _call_state_machine_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'call_sid', 'current_state']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'call_sid': {'required': True}, 'current_state': {'allowed_values': ['queued', 'dialing', 'answered', 'pitched', 'qualified', 'transferred', 'callback', 'closed'], 'required': True}, 'previous_state': {'allowed_values': ['queued', 'dialing', 'answered', 'pitched', 'qualified', 'transferred', 'callback', 'closed']}, 'window_state': {'allowed_values': ['open', 'closed']}, 'attempt_count': {'min': 0, 'max': 3}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/call_state_machine")
async def call_state_machine_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("call_state_machine", payload)
    _call_state_machine_edge_guard(payload)
    CAPABILITY_ID = "call_state_machine"
    handle = _call_state_machine_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("call_state_machine", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/call_state_machine")
def call_state_machine_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["call_state_machine"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("call_state_machine", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/call_state_machine/{item_id}")
def call_state_machine_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("call_state_machine", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/call_state_machine/{item_id}")
async def call_state_machine_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "call_state_machine", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "call_state_machine", "result": result}


@router.delete("/call_state_machine/{item_id}")
async def call_state_machine_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "call_state_machine", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "call_state_machine", "result": result}


# --- project_knowledge_grounding ---


def _project_knowledge_grounding_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.project_knowledge_grounding import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _project_knowledge_grounding_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'project_tag', 'claim_type', 'question']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'project_tag': {'required': True}, 'claim_type': {'allowed_values': ['price', 'payment_plan', 'handover_date', 'other'], 'required': True}, 'question': {'required': True}, 'authority_label': {'allowed_values': ['certified', 'documents', 'formulas', 'procedures']}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/project_knowledge_grounding")
async def project_knowledge_grounding_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("project_knowledge_grounding", payload)
    _project_knowledge_grounding_edge_guard(payload)
    CAPABILITY_ID = "project_knowledge_grounding"
    handle = _project_knowledge_grounding_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("project_knowledge_grounding", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/project_knowledge_grounding")
def project_knowledge_grounding_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["project_knowledge_grounding"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("project_knowledge_grounding", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/project_knowledge_grounding/{item_id}")
def project_knowledge_grounding_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("project_knowledge_grounding", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/project_knowledge_grounding/{item_id}")
async def project_knowledge_grounding_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "project_knowledge_grounding", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "project_knowledge_grounding", "result": result}


@router.delete("/project_knowledge_grounding/{item_id}")
async def project_knowledge_grounding_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "project_knowledge_grounding", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "project_knowledge_grounding", "result": result}


# --- voice_gateway ---


def _voice_gateway_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.voice_gateway import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _voice_gateway_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'language']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'direction': {'allowed_values': ['outbound', 'inbound']}, 'language': {'allowed_values': ['en', 'ar'], 'required': True}, 'asr_engine': {'allowed_values': ['twilio_gather_speech']}, 'twilio_mode': {'allowed_values': ['stubbed', 'live']}, 'call_status': {'allowed_values': ['initiated', 'ringing', 'answered', 'completed', 'failed', 'busy', 'no-answer']}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/voice_gateway")
async def voice_gateway_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("voice_gateway", payload)
    _voice_gateway_edge_guard(payload)
    CAPABILITY_ID = "voice_gateway"
    handle = _voice_gateway_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("voice_gateway", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/voice_gateway")
def voice_gateway_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["voice_gateway"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("voice_gateway", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/voice_gateway/{item_id}")
def voice_gateway_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("voice_gateway", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/voice_gateway/{item_id}")
async def voice_gateway_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "voice_gateway", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "voice_gateway", "result": result}


@router.delete("/voice_gateway/{item_id}")
async def voice_gateway_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "voice_gateway", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "voice_gateway", "result": result}


# --- warm_transfer ---


def _warm_transfer_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.warm_transfer import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _warm_transfer_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'call_sid', 'outcome', 'summary']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'call_sid': {'required': True}, 'outcome': {'allowed_values': ['project_interested', 'other_re_interested', 'not_interested'], 'required': True}, 'summary': {'required': True}, 'transfer_status': {'allowed_values': ['initiated', 'bridged', 'failed', 'declined']}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/warm_transfer")
async def warm_transfer_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("warm_transfer", payload)
    _warm_transfer_edge_guard(payload)
    CAPABILITY_ID = "warm_transfer"
    handle = _warm_transfer_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("warm_transfer", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/warm_transfer")
def warm_transfer_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["warm_transfer"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("warm_transfer", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/warm_transfer/{item_id}")
def warm_transfer_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("warm_transfer", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/warm_transfer/{item_id}")
async def warm_transfer_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "warm_transfer", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "warm_transfer", "result": result}


@router.delete("/warm_transfer/{item_id}")
async def warm_transfer_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "warm_transfer", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "warm_transfer", "result": result}


# --- qualification_and_broker_summary ---


def _qualification_and_broker_summary_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.qualification_and_broker_summary import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _qualification_and_broker_summary_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'call_sid', 'outcome']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'call_sid': {'required': True}, 'outcome': {'allowed_values': ['project_interested', 'other_re_interested', 'not_interested'], 'required': True}, 'property_type': {'allowed_values': ['apartment', 'villa', 'townhouse', 'plot', 'office']}, 'budget': {'min': 0.0}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/qualification_and_broker_summary")
async def qualification_and_broker_summary_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("qualification_and_broker_summary", payload)
    _qualification_and_broker_summary_edge_guard(payload)
    CAPABILITY_ID = "qualification_and_broker_summary"
    handle = _qualification_and_broker_summary_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("qualification_and_broker_summary", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/qualification_and_broker_summary")
def qualification_and_broker_summary_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["qualification_and_broker_summary"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("qualification_and_broker_summary", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/qualification_and_broker_summary/{item_id}")
def qualification_and_broker_summary_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("qualification_and_broker_summary", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/qualification_and_broker_summary/{item_id}")
async def qualification_and_broker_summary_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "qualification_and_broker_summary", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "qualification_and_broker_summary", "result": result}


@router.delete("/qualification_and_broker_summary/{item_id}")
async def qualification_and_broker_summary_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "qualification_and_broker_summary", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "qualification_and_broker_summary", "result": result}


# --- outcome_capture_and_ledger ---


def _outcome_capture_and_ledger_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.outcome_capture_and_ledger import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _outcome_capture_and_ledger_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'call_sid', 'event_type']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'call_sid': {'required': True}, 'event_type': {'allowed_values': ['attempt', 'answer', 'outcome', 'transfer', 'disposition'], 'required': True}, 'outcome': {'allowed_values': ['project_interested', 'other_re_interested', 'not_interested']}, 'attempt_count': {'min': 0, 'max': 3}, 'ledger_index': {'min': 0}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/outcome_capture_and_ledger")
async def outcome_capture_and_ledger_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("outcome_capture_and_ledger", payload)
    _outcome_capture_and_ledger_edge_guard(payload)
    CAPABILITY_ID = "outcome_capture_and_ledger"
    handle = _outcome_capture_and_ledger_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("outcome_capture_and_ledger", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/outcome_capture_and_ledger")
def outcome_capture_and_ledger_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["outcome_capture_and_ledger"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("outcome_capture_and_ledger", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/outcome_capture_and_ledger/{item_id}")
def outcome_capture_and_ledger_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("outcome_capture_and_ledger", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/outcome_capture_and_ledger/{item_id}")
async def outcome_capture_and_ledger_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "outcome_capture_and_ledger", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "outcome_capture_and_ledger", "result": result}


@router.delete("/outcome_capture_and_ledger/{item_id}")
async def outcome_capture_and_ledger_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "outcome_capture_and_ledger", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "outcome_capture_and_ledger", "result": result}


# --- crm_destination_placeholder ---


def _crm_destination_placeholder_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.crm_destination_placeholder import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _crm_destination_placeholder_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'crm_system']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'crm_system': {'allowed_values': ['unstated', 'salesforce', 'hubspot', 'zoho'], 'required': True}, 'delivery_state': {'allowed_values': ['queued', 'stubbed', 'refused']}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/crm_destination_placeholder")
async def crm_destination_placeholder_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("crm_destination_placeholder", payload)
    _crm_destination_placeholder_edge_guard(payload)
    CAPABILITY_ID = "crm_destination_placeholder"
    handle = _crm_destination_placeholder_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("crm_destination_placeholder", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/crm_destination_placeholder")
def crm_destination_placeholder_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["crm_destination_placeholder"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("crm_destination_placeholder", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/crm_destination_placeholder/{item_id}")
def crm_destination_placeholder_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("crm_destination_placeholder", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/crm_destination_placeholder/{item_id}")
async def crm_destination_placeholder_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "crm_destination_placeholder", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "crm_destination_placeholder", "result": result}


@router.delete("/crm_destination_placeholder/{item_id}")
async def crm_destination_placeholder_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "crm_destination_placeholder", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "crm_destination_placeholder", "result": result}


# --- notification ---


def _notification_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.notification import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _notification_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'channel', 'trigger_event']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'channel': {'allowed_values': ['email', 'sms', 'mcp', 'webhook'], 'required': True}, 'trigger_event': {'allowed_values': ['lead_qualified', 'transfer_completed', 'call_failed', 'campaign_summary'], 'required': True}, 'delivery_state': {'allowed_values': ['queued', 'sent', 'failed']}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/notification")
async def notification_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("notification", payload)
    _notification_edge_guard(payload)
    CAPABILITY_ID = "notification"
    handle = _notification_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("notification", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/notification")
def notification_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["notification"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("notification", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/notification/{item_id}")
def notification_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("notification", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/notification/{item_id}")
async def notification_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "notification", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "notification", "result": result}


@router.delete("/notification/{item_id}")
async def notification_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "notification", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "notification", "result": result}


# --- local_drive ---


def _local_drive_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.local_drive import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _local_drive_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'relative_path', 'operation']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'relative_path': {'required': True}, 'operation': {'allowed_values': ['read', 'write', 'list', 'delete'], 'required': True}, 'bytes_written': {'min': 0}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/local_drive")
async def local_drive_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("local_drive", payload)
    _local_drive_edge_guard(payload)
    CAPABILITY_ID = "local_drive"
    handle = _local_drive_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("local_drive", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/local_drive")
def local_drive_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["local_drive"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("local_drive", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/local_drive/{item_id}")
def local_drive_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("local_drive", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/local_drive/{item_id}")
async def local_drive_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "local_drive", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "local_drive", "result": result}


@router.delete("/local_drive/{item_id}")
async def local_drive_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "local_drive", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "local_drive", "result": result}


# --- google_drive ---


def _google_drive_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.google_drive import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _google_drive_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'drive_mode', 'operation']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    # Credentials are deploy-time settings read from the environment, never
    # fields the caller must send: requiring them here would make this route
    # refuse a payload built from its own schema (the spec does not and
    # cannot carry them -- app.factory.build.block_inputs.handler_required_
    # fields drops any name the handler reads from os.environ).
    constraints = {'GOOGLE_CLIENT_ID': {'required': False}, 'GOOGLE_CLIENT_SECRET': {'required': False}, 'GOOGLE_REFRESH_TOKEN': {'required': False}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'drive_mode': {'allowed_values': ['stubbed', 'live'], 'required': True}, 'operation': {'allowed_values': ['upload', 'download', 'list'], 'required': True}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/google_drive")
async def google_drive_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("google_drive", payload)
    _google_drive_edge_guard(payload)
    CAPABILITY_ID = "google_drive"
    handle = _google_drive_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("google_drive", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/google_drive")
def google_drive_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["google_drive"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("google_drive", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/google_drive/{item_id}")
def google_drive_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("google_drive", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/google_drive/{item_id}")
async def google_drive_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "google_drive", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "google_drive", "result": result}


@router.delete("/google_drive/{item_id}")
async def google_drive_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "google_drive", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "google_drive", "result": result}


# --- mcp_adapter ---


def _mcp_adapter_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.mcp_adapter import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _mcp_adapter_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models``. This section carries its own copy for one reason: the
    factory reads the capability's route source to build the sample payload
    it POSTs, and a contract that lives only in the model is a contract the
    sample cannot see -- the edge then refuses it.
    """
    required_fields = ['reference', 'status', 'catalog_scope']
    for _name in required_fields:
        if _name not in payload or payload[_name] in (None, ""):
            raise HTTPException(status_code=422,
                                detail="Missing required field: " + _name)
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'catalog_scope': {'allowed_values': ['platform', 'vendor', 'tenant'], 'required': True}}
    for _name, _rules in constraints.items():
        if _name not in payload:
            continue
        _value = payload[_name]
        _allowed = _rules.get("allowed_values")
        if _allowed is not None and _value not in _allowed:
            raise HTTPException(status_code=422,
                                detail=_name + " must be one of: "
                                + ", ".join(str(v) for v in _allowed))
        _low, _high = _rules.get("min"), _rules.get("max")
        if isinstance(_value, bool):
            continue
        if not isinstance(_value, (int, float)):
            continue
        if _low is not None and _value < _low:
            raise HTTPException(status_code=422, detail=_name + " is below the minimum")
        if _high is not None and _value > _high:
            raise HTTPException(status_code=422, detail=_name + " is above the maximum")


@router.post("/mcp_adapter")
async def mcp_adapter_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("mcp_adapter", payload)
    _mcp_adapter_edge_guard(payload)
    CAPABILITY_ID = "mcp_adapter"
    handle = _mcp_adapter_handle
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("mcp_adapter", record, tenant_id=tenant.tenant_id)

    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    # id is the persisted row's id: the acceptance probes and the
    # operator console read the created record back by it, and a response
    # that hides it forces every caller to list-and-guess.
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "id": stored.get("id") if isinstance(stored, dict) else None,
            "stored": stored}


@router.get("/mcp_adapter")
def mcp_adapter_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["mcp_adapter"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("mcp_adapter", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/mcp_adapter/{item_id}")
def mcp_adapter_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    record = store.get("mcp_adapter", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/mcp_adapter/{item_id}")
async def mcp_adapter_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "mcp_adapter", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "mcp_adapter", "result": result}


@router.delete("/mcp_adapter/{item_id}")
async def mcp_adapter_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "mcp_adapter", {'id': item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "capability": "mcp_adapter", "result": result}


@router.post("/work_queue")
async def work_queue_enqueue(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain(
        "enqueue", str((payload or {}).get("capability_id") or ""), payload or {},
        context=product_context(request),
    )
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "result": result}


@router.post("/work_queue/{item_id}/process")
async def work_queue_process(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("process", "", {"id": item_id}, context=product_context(request))
    if result.get("status") != "success":
        return {"ok": False,
                "error": result.get("error_message") or result.get("status"),
                "result": result}
    return {"ok": True, "result": result}


@router.get("/work_queue")
def work_queue_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    from app import work_queue as _work_queue
    return {"items": _work_queue.list_all(tenant_id=tenant.tenant_id)}



# --- Layer 4: campaign outcome metrics ------------------------------------
#
# The numbers the brokerage manager reads: attempted, answered, the
# three-outcome interest split, transfers and conversion -- per campaign.
# This is a read model over the ledger the calls already wrote
# (``outcome_capture_and_ledger``), scoped to the authenticated principal's
# tenant like every other read on this surface. It is deliberately not a
# capability: it persists nothing, so it has no entity, no model and no row.
# The arithmetic lives in app/analytics_metrics.py; the formula lives in
# app/formulas.py; the answer carries its precedence.v1 layer (``formulas``).


@router.get("/analytics/campaign_metrics")
def analytics_campaign_metrics(request: Request) -> Dict[str, Any]:
    """Per-campaign attempted / answered / interest split / transfers / conversion."""
    from app.auth import require_read_tenant
    tenant = require_read_tenant(request)
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k != "campaign")
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    from app import analytics_metrics
    rows = store.list_all("outcome_capture_and_ledger", tenant.tenant_id)
    return analytics_metrics.campaign_metrics(rows, campaign=given.get("campaign"))
