"""HTTP surface for the hotel operations platform.

Kernel routes publish each build role's job description. Capability routes are
tenant-scoped: the caller's tenant is resolved from the bearer token, the
payload is validated against the capability's own model (422), the handler
dispatches to the vendored blocks, and only then is the request persisted with
the route's tenant-scoped ``save(payload)``. A cross-tenant read answers 404:
tenancy is resolved from the principal, never from the payload.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app import jobs, store

router = APIRouter()


@router.get("/jobs")
def list_jobs() -> Dict[str, Any]:
    """Roster of every kernel job description."""
    return {"jobs": jobs.JOBS}


@router.get("/catalog")
def catalog() -> Dict[str, Any]:
    """COLLECTOR -- Binding surveyor."""
    return jobs.CATALOG


@router.get("/inventory")
def inventory() -> Dict[str, Any]:
    """CLONER -- Block stocker. Pinned vendor lock, read live."""
    return jobs.inventory()


@router.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    """WRITER -- Platform manufacturer. Capability HTTP surface."""
    return {"items": jobs.CAPABILITIES}


@router.get("/gates")
def gates() -> Dict[str, Any]:
    """TESTER -- Acceptance inspector. Coverage only; does not run tests."""
    return jobs.GATES


@router.get("/provenance")
def provenance() -> Dict[str, Any]:
    """STORE_MANAGER -- Store registrar. Clone register and provenance."""
    return jobs.provenance()



# --- property_and_room_registry ---


def _property_and_room_registry_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.property_and_room_registry import handle as _handle

        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _property_and_room_registry_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models.PropertyAndRoomRegistry``. This section carries its own copy for one
    reason: the factory reads the capability's route source to build the
    sample payload it POSTs, and a contract that lives only in the model
    is a contract the sample cannot see -- the edge then refuses it.
    """
    constraints = {
        'reference': {'required': True},
        'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
        'property_name': {'required': True},
        'building': {'required': False},
        'floor': {'min': 0, 'max': 200, 'required': False},
        'room_number': {'required': True},
        'room_type': {'allowed_values': ['standard', 'superior', 'deluxe', 'suite', 'accessible'], 'required': True},
        'capacity': {'min': 1, 'max': 12, 'required': False},
        'room_status': {'allowed_values': ['available', 'occupied', 'dirty', 'cleaned', 'out_of_order'], 'required': True},
        'notes': {'required': False},
    }
    for _name, _rules in constraints.items():
        _value = payload.get(_name)
        if _value in (None, ""):
            if _rules.get("required"):
                raise HTTPException(
                    status_code=422,
                    detail="required field is absent: " + _name,
                )
            continue
        _allowed = _rules.get("allowed_values")
        if _allowed and _value not in _allowed:
            raise HTTPException(
                status_code=422,
                detail="undeclared value for " + _name,
            )
    _value = payload.get('floor')
    if _value not in (None, "") and not isinstance(payload.get('floor'), int):
        raise HTTPException(status_code=422, detail='floor must be an integer')
    _value = payload.get('capacity')
    if _value not in (None, "") and not isinstance(payload.get('capacity'), int):
        raise HTTPException(status_code=422, detail='capacity must be an integer')


@router.post("/property_and_room_registry")
async def property_and_room_registry_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("property_and_room_registry", payload)
    _property_and_room_registry_edge_guard(payload)
    CAPABILITY_ID = "property_and_room_registry"
    handle = _property_and_room_registry_handle

    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("property_and_room_registry", record, tenant_id=tenant.tenant_id)

    result = handle(payload)
    if result.get("ok") is False:
        return {"ok": False,
                "error": str(result.get("error") or "refused"),
                "capability": CAPABILITY_ID,
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/property_and_room_registry")
def property_and_room_registry_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["property_and_room_registry"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("property_and_room_registry", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/property_and_room_registry/{item_id}")
def property_and_room_registry_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    record = store.get("property_and_room_registry", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/property_and_room_registry/{item_id}")
def property_and_room_registry_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("property_and_room_registry", payload)
    _property_and_room_registry_edge_guard(payload)
    updated = store.update("property_and_room_registry", item_id, payload, tenant.tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "property_and_room_registry", "stored": updated}


@router.delete("/property_and_room_registry/{item_id}")
def property_and_room_registry_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    if not store.delete("property_and_room_registry", item_id, tenant.tenant_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "property_and_room_registry", "deleted": item_id}


# --- front_desk_and_guest_stay ---


def _front_desk_and_guest_stay_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.front_desk_and_guest_stay import handle as _handle

        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _front_desk_and_guest_stay_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models.FrontDeskAndGuestStay``. This section carries its own copy for one
    reason: the factory reads the capability's route source to build the
    sample payload it POSTs, and a contract that lives only in the model
    is a contract the sample cannot see -- the edge then refuses it.
    """
    constraints = {
        'reference': {'required': True},
        'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
        'guest_name': {'required': True},
        'room_number': {'required': True},
        'arrival_date': {'required': True},
        'departure_date': {'required': False},
        'guests_count': {'min': 1, 'max': 10, 'required': False},
        'stay_status': {'allowed_values': ['reserved', 'checked_in', 'checked_out', 'no_show', 'cancelled'], 'required': True},
        'folio_currency': {'required': False},
        'notes': {'required': False},
    }
    for _name, _rules in constraints.items():
        _value = payload.get(_name)
        if _value in (None, ""):
            if _rules.get("required"):
                raise HTTPException(
                    status_code=422,
                    detail="required field is absent: " + _name,
                )
            continue
        _allowed = _rules.get("allowed_values")
        if _allowed and _value not in _allowed:
            raise HTTPException(
                status_code=422,
                detail="undeclared value for " + _name,
            )
    _value = payload.get('guests_count')
    if _value not in (None, "") and not isinstance(payload.get('guests_count'), int):
        raise HTTPException(status_code=422, detail='guests_count must be an integer')


@router.post("/front_desk_and_guest_stay")
async def front_desk_and_guest_stay_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("front_desk_and_guest_stay", payload)
    _front_desk_and_guest_stay_edge_guard(payload)
    CAPABILITY_ID = "front_desk_and_guest_stay"
    handle = _front_desk_and_guest_stay_handle

    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("front_desk_and_guest_stay", record, tenant_id=tenant.tenant_id)

    result = handle(payload)
    if result.get("ok") is False:
        return {"ok": False,
                "error": str(result.get("error") or "refused"),
                "capability": CAPABILITY_ID,
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/front_desk_and_guest_stay")
def front_desk_and_guest_stay_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["front_desk_and_guest_stay"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("front_desk_and_guest_stay", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/front_desk_and_guest_stay/{item_id}")
def front_desk_and_guest_stay_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    record = store.get("front_desk_and_guest_stay", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/front_desk_and_guest_stay/{item_id}")
def front_desk_and_guest_stay_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("front_desk_and_guest_stay", payload)
    _front_desk_and_guest_stay_edge_guard(payload)
    updated = store.update("front_desk_and_guest_stay", item_id, payload, tenant.tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "front_desk_and_guest_stay", "stored": updated}


@router.delete("/front_desk_and_guest_stay/{item_id}")
def front_desk_and_guest_stay_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    if not store.delete("front_desk_and_guest_stay", item_id, tenant.tenant_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "front_desk_and_guest_stay", "deleted": item_id}


# --- housekeeping_and_maintenance ---


def _housekeeping_and_maintenance_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.housekeeping_and_maintenance import handle as _handle

        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _housekeeping_and_maintenance_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models.HousekeepingAndMaintenance``. This section carries its own copy for one
    reason: the factory reads the capability's route source to build the
    sample payload it POSTs, and a contract that lives only in the model
    is a contract the sample cannot see -- the edge then refuses it.
    """
    constraints = {
        'reference': {'required': True},
        'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
        'title': {'required': True},
        'work_type': {'allowed_values': ['housekeeping', 'maintenance', 'inspection'], 'required': True},
        'room_number': {'required': True},
        'priority': {'allowed_values': ['low', 'normal', 'high', 'urgent'], 'required': True},
        'due_date': {'required': False},
        'assigned_to': {'required': False},
        'work_status': {'allowed_values': ['open', 'assigned', 'in_progress', 'done', 'cancelled'], 'required': True},
        'notes': {'required': False},
    }
    for _name, _rules in constraints.items():
        _value = payload.get(_name)
        if _value in (None, ""):
            if _rules.get("required"):
                raise HTTPException(
                    status_code=422,
                    detail="required field is absent: " + _name,
                )
            continue
        _allowed = _rules.get("allowed_values")
        if _allowed and _value not in _allowed:
            raise HTTPException(
                status_code=422,
                detail="undeclared value for " + _name,
            )



@router.post("/housekeeping_and_maintenance")
async def housekeeping_and_maintenance_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("housekeeping_and_maintenance", payload)
    _housekeeping_and_maintenance_edge_guard(payload)
    CAPABILITY_ID = "housekeeping_and_maintenance"
    handle = _housekeeping_and_maintenance_handle

    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("housekeeping_and_maintenance", record, tenant_id=tenant.tenant_id)

    result = handle(payload)
    if result.get("ok") is False:
        return {"ok": False,
                "error": str(result.get("error") or "refused"),
                "capability": CAPABILITY_ID,
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/housekeeping_and_maintenance")
def housekeeping_and_maintenance_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["housekeeping_and_maintenance"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("housekeeping_and_maintenance", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/housekeeping_and_maintenance/{item_id}")
def housekeeping_and_maintenance_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    record = store.get("housekeeping_and_maintenance", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/housekeeping_and_maintenance/{item_id}")
def housekeeping_and_maintenance_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("housekeeping_and_maintenance", payload)
    _housekeeping_and_maintenance_edge_guard(payload)
    updated = store.update("housekeeping_and_maintenance", item_id, payload, tenant.tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "housekeeping_and_maintenance", "stored": updated}


@router.delete("/housekeeping_and_maintenance/{item_id}")
def housekeeping_and_maintenance_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    if not store.delete("housekeeping_and_maintenance", item_id, tenant.tenant_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "housekeeping_and_maintenance", "deleted": item_id}


# --- guest_engagement_and_segmentation ---


def _guest_engagement_and_segmentation_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.guest_engagement_and_segmentation import handle as _handle

        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _guest_engagement_and_segmentation_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models.GuestEngagementAndSegmentation``. This section carries its own copy for one
    reason: the factory reads the capability's route source to build the
    sample payload it POSTs, and a contract that lives only in the model
    is a contract the sample cannot see -- the edge then refuses it.
    """
    constraints = {
        'reference': {'required': True},
        'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
        'guest_name': {'required': True},
        'recency_days': {'min': 0, 'max': 3650, 'required': True},
        'frequency': {'min': 0, 'max': 1000, 'required': True},
        'monetary': {'min': 0.0, 'max': 1000000.0, 'required': True},
        'segment': {'allowed_values': ['champion', 'loyal', 'potential', 'at_risk', 'dormant'], 'required': False},
        'delivery_channel': {'allowed_values': ['mcp', 'email'], 'required': True},
        'offer_code': {'required': False},
        'notes': {'required': False},
    }
    for _name, _rules in constraints.items():
        _value = payload.get(_name)
        if _value in (None, ""):
            if _rules.get("required"):
                raise HTTPException(
                    status_code=422,
                    detail="required field is absent: " + _name,
                )
            continue
        _allowed = _rules.get("allowed_values")
        if _allowed and _value not in _allowed:
            raise HTTPException(
                status_code=422,
                detail="undeclared value for " + _name,
            )
    _value = payload.get('recency_days')
    if _value not in (None, "") and not isinstance(payload.get('recency_days'), int):
        raise HTTPException(status_code=422, detail='recency_days must be an integer')
    _value = payload.get('frequency')
    if _value not in (None, "") and not isinstance(payload.get('frequency'), int):
        raise HTTPException(status_code=422, detail='frequency must be an integer')
    _value = payload.get('monetary')
    if _value not in (None, "") and not isinstance(payload.get('monetary'), int) and not isinstance(payload.get('monetary'), float):
        raise HTTPException(status_code=422, detail='monetary must be a number')


@router.post("/guest_engagement_and_segmentation")
async def guest_engagement_and_segmentation_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("guest_engagement_and_segmentation", payload)
    _guest_engagement_and_segmentation_edge_guard(payload)
    CAPABILITY_ID = "guest_engagement_and_segmentation"
    handle = _guest_engagement_and_segmentation_handle

    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("guest_engagement_and_segmentation", record, tenant_id=tenant.tenant_id)

    result = handle(payload)
    if result.get("ok") is False:
        return {"ok": False,
                "error": str(result.get("error") or "refused"),
                "capability": CAPABILITY_ID,
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/guest_engagement_and_segmentation")
def guest_engagement_and_segmentation_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["guest_engagement_and_segmentation"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("guest_engagement_and_segmentation", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/guest_engagement_and_segmentation/{item_id}")
def guest_engagement_and_segmentation_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    record = store.get("guest_engagement_and_segmentation", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/guest_engagement_and_segmentation/{item_id}")
def guest_engagement_and_segmentation_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("guest_engagement_and_segmentation", payload)
    _guest_engagement_and_segmentation_edge_guard(payload)
    updated = store.update("guest_engagement_and_segmentation", item_id, payload, tenant.tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "guest_engagement_and_segmentation", "stored": updated}


@router.delete("/guest_engagement_and_segmentation/{item_id}")
def guest_engagement_and_segmentation_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    if not store.delete("guest_engagement_and_segmentation", item_id, tenant.tenant_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "guest_engagement_and_segmentation", "deleted": item_id}


# --- document_and_knowledge_answers ---


def _document_and_knowledge_answers_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.document_and_knowledge_answers import handle as _handle

        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _document_and_knowledge_answers_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models.DocumentAndKnowledgeAnswers``. This section carries its own copy for one
    reason: the factory reads the capability's route source to build the
    sample payload it POSTs, and a contract that lives only in the model
    is a contract the sample cannot see -- the edge then refuses it.
    """
    constraints = {
        'reference': {'required': True},
        'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
        'title': {'required': True},
        'document_kind': {'allowed_values': ['manual', 'sop', 'rate_sheet', 'policy', 'other'], 'required': True},
        'question': {'required': True},
        'document_text': {'required': True},
        'attachment_path': {'required': False},
        'answer': {'required': False},
        'source_document': {'required': False},
        'authority_label': {'allowed_values': ['certified', 'documents', 'formulas', 'procedures'], 'required': False},
        'notes': {'required': False},
    }
    for _name, _rules in constraints.items():
        _value = payload.get(_name)
        if _value in (None, ""):
            if _rules.get("required"):
                raise HTTPException(
                    status_code=422,
                    detail="required field is absent: " + _name,
                )
            continue
        _allowed = _rules.get("allowed_values")
        if _allowed and _value not in _allowed:
            raise HTTPException(
                status_code=422,
                detail="undeclared value for " + _name,
            )



@router.post("/document_and_knowledge_answers")
async def document_and_knowledge_answers_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("document_and_knowledge_answers", payload)
    _document_and_knowledge_answers_edge_guard(payload)
    CAPABILITY_ID = "document_and_knowledge_answers"
    handle = _document_and_knowledge_answers_handle

    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("document_and_knowledge_answers", record, tenant_id=tenant.tenant_id)

    result = handle(payload)
    if result.get("ok") is False:
        return {"ok": False,
                "error": str(result.get("error") or "refused"),
                "capability": CAPABILITY_ID,
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/document_and_knowledge_answers")
def document_and_knowledge_answers_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["document_and_knowledge_answers"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("document_and_knowledge_answers", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/document_and_knowledge_answers/{item_id}")
def document_and_knowledge_answers_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    record = store.get("document_and_knowledge_answers", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/document_and_knowledge_answers/{item_id}")
def document_and_knowledge_answers_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("document_and_knowledge_answers", payload)
    _document_and_knowledge_answers_edge_guard(payload)
    updated = store.update("document_and_knowledge_answers", item_id, payload, tenant.tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "document_and_knowledge_answers", "stored": updated}


@router.delete("/document_and_knowledge_answers/{item_id}")
def document_and_knowledge_answers_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    if not store.delete("document_and_knowledge_answers", item_id, tenant.tenant_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "document_and_knowledge_answers", "deleted": item_id}


# --- operations_billing ---


def _operations_billing_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.operations_billing import handle as _handle

        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _operations_billing_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models.OperationsBilling``. This section carries its own copy for one
    reason: the factory reads the capability's route source to build the
    sample payload it POSTs, and a contract that lives only in the model
    is a contract the sample cannot see -- the edge then refuses it.
    """
    constraints = {
        'setting': {'required': True},
        'reference': {'required': True},
        'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
        'folio_reference': {'required': True},
        'charge_type': {'allowed_values': ['room', 'food_and_beverage', 'spa', 'minibar', 'laundry', 'other'], 'required': True},
        'amount': {'min': 0.0, 'max': 1000000.0, 'required': True},
        'currency': {'required': False},
        'tax_rate_percent': {'min': 0.0, 'max': 100.0, 'required': False},
        'total_amount': {'min': 0.0, 'required': False},
        'notes': {'required': False},
    }
    for _name, _rules in constraints.items():
        _value = payload.get(_name)
        if _value in (None, ""):
            if _rules.get("required"):
                raise HTTPException(
                    status_code=422,
                    detail="required field is absent: " + _name,
                )
            continue
        _allowed = _rules.get("allowed_values")
        if _allowed and _value not in _allowed:
            raise HTTPException(
                status_code=422,
                detail="undeclared value for " + _name,
            )
    _value = payload.get('amount')
    if _value not in (None, "") and not isinstance(payload.get('amount'), int) and not isinstance(payload.get('amount'), float):
        raise HTTPException(status_code=422, detail='amount must be a number')
    _value = payload.get('tax_rate_percent')
    if _value not in (None, "") and not isinstance(payload.get('tax_rate_percent'), int) and not isinstance(payload.get('tax_rate_percent'), float):
        raise HTTPException(status_code=422, detail='tax_rate_percent must be a number')
    _value = payload.get('total_amount')
    if _value not in (None, "") and not isinstance(payload.get('total_amount'), int) and not isinstance(payload.get('total_amount'), float):
        raise HTTPException(status_code=422, detail='total_amount must be a number')


@router.post("/operations_billing")
async def operations_billing_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("operations_billing", payload)
    _operations_billing_edge_guard(payload)
    CAPABILITY_ID = "operations_billing"
    handle = _operations_billing_handle

    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("operations_billing", record, tenant_id=tenant.tenant_id)

    result = handle(payload)
    if result.get("ok") is False:
        return {"ok": False,
                "error": str(result.get("error") or "refused"),
                "capability": CAPABILITY_ID,
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/operations_billing")
def operations_billing_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["operations_billing"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("operations_billing", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/operations_billing/{item_id}")
def operations_billing_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    record = store.get("operations_billing", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/operations_billing/{item_id}")
def operations_billing_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("operations_billing", payload)
    _operations_billing_edge_guard(payload)
    updated = store.update("operations_billing", item_id, payload, tenant.tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "operations_billing", "stored": updated}


@router.delete("/operations_billing/{item_id}")
def operations_billing_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    if not store.delete("operations_billing", item_id, tenant.tenant_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "operations_billing", "deleted": item_id}


# --- operations_oversight_dashboard ---


def _operations_oversight_dashboard_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.operations_oversight_dashboard import handle as _handle

        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _operations_oversight_dashboard_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models.OperationsOversightDashboard``. This section carries its own copy for one
    reason: the factory reads the capability's route source to build the
    sample payload it POSTs, and a contract that lives only in the model
    is a contract the sample cannot see -- the edge then refuses it.
    """
    constraints = {
        'reference': {'required': True},
        'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
        'dashboard_name': {'required': True},
        'widget': {'allowed_values': ['occupancy', 'room_status', 'work_orders', 'guest_activity'], 'required': True},
        'window_days': {'min': 1, 'max': 90, 'required': False},
        'operator_role': {'allowed_values': ['operator', 'admin'], 'required': True},
        'occupancy_percent': {'min': 0.0, 'max': 100.0, 'required': False},
        'open_work_orders': {'min': 0, 'max': 10000, 'required': False},
        'notes': {'required': False},
    }
    for _name, _rules in constraints.items():
        _value = payload.get(_name)
        if _value in (None, ""):
            if _rules.get("required"):
                raise HTTPException(
                    status_code=422,
                    detail="required field is absent: " + _name,
                )
            continue
        _allowed = _rules.get("allowed_values")
        if _allowed and _value not in _allowed:
            raise HTTPException(
                status_code=422,
                detail="undeclared value for " + _name,
            )
    _value = payload.get('window_days')
    if _value not in (None, "") and not isinstance(payload.get('window_days'), int):
        raise HTTPException(status_code=422, detail='window_days must be an integer')
    _value = payload.get('occupancy_percent')
    if _value not in (None, "") and not isinstance(payload.get('occupancy_percent'), int) and not isinstance(payload.get('occupancy_percent'), float):
        raise HTTPException(status_code=422, detail='occupancy_percent must be a number')
    _value = payload.get('open_work_orders')
    if _value not in (None, "") and not isinstance(payload.get('open_work_orders'), int):
        raise HTTPException(status_code=422, detail='open_work_orders must be an integer')


@router.post("/operations_oversight_dashboard")
async def operations_oversight_dashboard_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("operations_oversight_dashboard", payload)
    _operations_oversight_dashboard_edge_guard(payload)
    CAPABILITY_ID = "operations_oversight_dashboard"
    handle = _operations_oversight_dashboard_handle

    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("operations_oversight_dashboard", record, tenant_id=tenant.tenant_id)

    result = handle(payload)
    if result.get("ok") is False:
        return {"ok": False,
                "error": str(result.get("error") or "refused"),
                "capability": CAPABILITY_ID,
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/operations_oversight_dashboard")
def operations_oversight_dashboard_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["operations_oversight_dashboard"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("operations_oversight_dashboard", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/operations_oversight_dashboard/{item_id}")
def operations_oversight_dashboard_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    record = store.get("operations_oversight_dashboard", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/operations_oversight_dashboard/{item_id}")
def operations_oversight_dashboard_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("operations_oversight_dashboard", payload)
    _operations_oversight_dashboard_edge_guard(payload)
    updated = store.update("operations_oversight_dashboard", item_id, payload, tenant.tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "operations_oversight_dashboard", "stored": updated}


@router.delete("/operations_oversight_dashboard/{item_id}")
def operations_oversight_dashboard_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    if not store.delete("operations_oversight_dashboard", item_id, tenant.tenant_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "operations_oversight_dashboard", "deleted": item_id}


# --- external_integration_adapter ---


def _external_integration_adapter_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.external_integration_adapter import handle as _handle

        result = _handle(payload)
    except Exception as exc:  # a block/runtime refusal is not an HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


def _external_integration_adapter_edge_guard(payload: Dict[str, Any]) -> None:
    """Refuse a record outside this capability's declared contract.

    ``app.auth.reject_invalid_payload`` enforces the same contract from
    ``app.models.ExternalIntegrationAdapter``. This section carries its own copy for one
    reason: the factory reads the capability's route source to build the
    sample payload it POSTs, and a contract that lives only in the model
    is a contract the sample cannot see -- the edge then refuses it.
    """
    constraints = {
        'reference': {'required': True},
        'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
        'system': {'allowed_values': ['opera', 'micros', 'maximo', 'loyalty_lms', 'grms', 'gaming_cms'], 'required': True},
        'resource': {'required': True},
        'direction': {'allowed_values': ['inbound', 'outbound'], 'required': True},
        'payload_format': {'allowed_values': ['json', 'csv', 'xml'], 'required': True},
        'endpoint_url': {'required': False},
        'records_seen': {'min': 0, 'required': False},
        'notes': {'required': False},
    }
    for _name, _rules in constraints.items():
        _value = payload.get(_name)
        if _value in (None, ""):
            if _rules.get("required"):
                raise HTTPException(
                    status_code=422,
                    detail="required field is absent: " + _name,
                )
            continue
        _allowed = _rules.get("allowed_values")
        if _allowed and _value not in _allowed:
            raise HTTPException(
                status_code=422,
                detail="undeclared value for " + _name,
            )
    _value = payload.get('records_seen')
    if _value not in (None, "") and not isinstance(payload.get('records_seen'), int):
        raise HTTPException(status_code=422, detail='records_seen must be an integer')


@router.post("/external_integration_adapter")
async def external_integration_adapter_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("external_integration_adapter", payload)
    _external_integration_adapter_edge_guard(payload)
    CAPABILITY_ID = "external_integration_adapter"
    handle = _external_integration_adapter_handle

    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        return store.save("external_integration_adapter", record, tenant_id=tenant.tenant_id)

    result = handle(payload)
    if result.get("ok") is False:
        return {"ok": False,
                "error": str(result.get("error") or "refused"),
                "capability": CAPABILITY_ID,
                "result": result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {"ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "capability": CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/external_integration_adapter")
def external_integration_adapter_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["external_integration_adapter"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("external_integration_adapter", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/external_integration_adapter/{item_id}")
def external_integration_adapter_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_read_tenant

    tenant = require_read_tenant(request)
    record = store.get("external_integration_adapter", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/external_integration_adapter/{item_id}")
def external_integration_adapter_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token

    tenant = require_platform_token(request)
    reject_invalid_payload("external_integration_adapter", payload)
    _external_integration_adapter_edge_guard(payload)
    updated = store.update("external_integration_adapter", item_id, payload, tenant.tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "external_integration_adapter", "stored": updated}


@router.delete("/external_integration_adapter/{item_id}")
def external_integration_adapter_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    if not store.delete("external_integration_adapter", item_id, tenant.tenant_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "capability": "external_integration_adapter", "deleted": item_id}



@router.get("/work_queue")
def work_queue_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    from app import work_queue as _work_queue

    return {"items": _work_queue.list_all(tenant_id=tenant.tenant_id)}


@router.post("/work_queue")
def work_queue_enqueue(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    from app import work_queue as _work_queue

    try:
        item = _work_queue.enqueue(
            str((payload or {}).get("capability_id") or ""),
            payload or {},
            tenant_id=tenant.tenant_id,
        )
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "item": item}


@router.post("/work_queue/{item_id}/process")
def work_queue_process(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    tenant = require_platform_token(request)
    from app import work_queue as _work_queue

    try:
        processed = _work_queue.process_pending(item_id, tenant_id=tenant.tenant_id)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if processed is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "item": processed}
