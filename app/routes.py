"""HTTP surface for the platform's kernels and capabilities.

Kernel routes publish each build role's job. Capability routes run
entirely in-process: the handler dispatches to a vendored block and
the result is persisted locally. No outbound call.

Tenancy: writes (POST / PUT / DELETE) require a platform token and the
row is written under the tenant that token resolves to. Reads resolve a
presented token the same way (an unknown token is 401); a read that
presents no token at all serves the platform's own front-desk tenant, so
the arrival-board display can poll without a per-user credential. No
caller ever names its own tenant in a payload or a query string.
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


# --- record_checkin (kernel execute_action template) ---


def _record_checkin_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.record_checkin import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/record_checkin")
async def record_checkin_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("record_checkin", payload)
    CAPABILITY_ID = "record_checkin"
    handle = _record_checkin_handle
    save = lambda record: store.save("record_checkin", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("record_checkin", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'guest_name', 'room_number', 'nights', 'arrival_time', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': True}, 'nights': {'min': 1, 'max': 30, 'required': True}, 'arrival_time': {'format': 'time', 'required': True}, 'notes': {'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/record_checkin")
def record_checkin_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["record_checkin"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("record_checkin", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/record_checkin/{item_id}")
def record_checkin_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("record_checkin", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/record_checkin/{item_id}")
async def record_checkin_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "record_checkin", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "record_checkin", 'result': result}


@router.delete("/record_checkin/{item_id}")
async def record_checkin_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "record_checkin", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "record_checkin", 'result': result}


# --- todays_arrivals_board (kernel execute_action template) ---


def _todays_arrivals_board_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.todays_arrivals_board import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/todays_arrivals_board")
async def todays_arrivals_board_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("todays_arrivals_board", payload)
    CAPABILITY_ID = "todays_arrivals_board"
    handle = _todays_arrivals_board_handle
    save = lambda record: store.save("todays_arrivals_board", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("todays_arrivals_board", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'arrival_date', 'guest_name', 'room_number', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'arrival_date': {'format': 'date', 'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': True}, 'arrived': {'required': False}, 'arrivals_count': {'min': 0, 'max': 200, 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/todays_arrivals_board")
def todays_arrivals_board_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["todays_arrivals_board"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("todays_arrivals_board", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/todays_arrivals_board/{item_id}")
def todays_arrivals_board_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("todays_arrivals_board", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/todays_arrivals_board/{item_id}")
async def todays_arrivals_board_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "todays_arrivals_board", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "todays_arrivals_board", 'result': result}


@router.delete("/todays_arrivals_board/{item_id}")
async def todays_arrivals_board_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "todays_arrivals_board", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "todays_arrivals_board", 'result': result}


# --- room_availability_check (kernel execute_action template) ---


def _room_availability_check_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.room_availability_check import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/room_availability_check")
async def room_availability_check_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("room_availability_check", payload)
    CAPABILITY_ID = "room_availability_check"
    handle = _room_availability_check_handle
    save = lambda record: store.save("room_availability_check", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("room_availability_check", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'room_number', 'check_in_date', 'check_out_date', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'room_number': {'required': True}, 'check_in_date': {'format': 'date', 'required': True}, 'check_out_date': {'format': 'date', 'required': True}, 'is_available': {'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/room_availability_check")
def room_availability_check_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["room_availability_check"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("room_availability_check", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/room_availability_check/{item_id}")
def room_availability_check_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("room_availability_check", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/room_availability_check/{item_id}")
async def room_availability_check_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "room_availability_check", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "room_availability_check", 'result': result}


@router.delete("/room_availability_check/{item_id}")
async def room_availability_check_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "room_availability_check", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "room_availability_check", 'result': result}


# --- guest_notes_and_preferences (kernel execute_action template) ---


def _guest_notes_and_preferences_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.guest_notes_and_preferences import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/guest_notes_and_preferences")
async def guest_notes_and_preferences_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("guest_notes_and_preferences", payload)
    CAPABILITY_ID = "guest_notes_and_preferences"
    handle = _guest_notes_and_preferences_handle
    save = lambda record: store.save("guest_notes_and_preferences", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("guest_notes_and_preferences", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'guest_name', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': False}, 'preference': {'required': False}, 'note': {'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/guest_notes_and_preferences")
def guest_notes_and_preferences_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["guest_notes_and_preferences"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("guest_notes_and_preferences", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/guest_notes_and_preferences/{item_id}")
def guest_notes_and_preferences_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("guest_notes_and_preferences", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/guest_notes_and_preferences/{item_id}")
async def guest_notes_and_preferences_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "guest_notes_and_preferences", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "guest_notes_and_preferences", 'result': result}


@router.delete("/guest_notes_and_preferences/{item_id}")
async def guest_notes_and_preferences_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "guest_notes_and_preferences", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "guest_notes_and_preferences", 'result': result}


# --- checkin_notifications (kernel execute_action template) ---


def _checkin_notifications_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.checkin_notifications import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/checkin_notifications")
async def checkin_notifications_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("checkin_notifications", payload)
    CAPABILITY_ID = "checkin_notifications"
    handle = _checkin_notifications_handle
    save = lambda record: store.save("checkin_notifications", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("checkin_notifications", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'guest_name', 'room_number', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': True}, 'channel': {'allowed_values': ['mcp', 'email'], 'required': False}, 'recipient': {'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/checkin_notifications")
def checkin_notifications_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["checkin_notifications"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("checkin_notifications", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/checkin_notifications/{item_id}")
def checkin_notifications_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("checkin_notifications", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/checkin_notifications/{item_id}")
async def checkin_notifications_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "checkin_notifications", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "checkin_notifications", 'result': result}


@router.delete("/checkin_notifications/{item_id}")
async def checkin_notifications_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "checkin_notifications", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "checkin_notifications", 'result': result}


# --- daily_checkin_summary (kernel execute_action template) ---


def _daily_checkin_summary_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.daily_checkin_summary import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/daily_checkin_summary")
async def daily_checkin_summary_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("daily_checkin_summary", payload)
    CAPABILITY_ID = "daily_checkin_summary"
    handle = _daily_checkin_summary_handle
    save = lambda record: store.save("daily_checkin_summary", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("daily_checkin_summary", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'summary_date', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'summary_date': {'format': 'date', 'required': True}, 'arrivals_count': {'min': 0, 'max': 500, 'required': False}, 'occupancy_percent': {'min': 0, 'max': 100, 'required': False}, 'no_show_count': {'min': 0, 'max': 100, 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/daily_checkin_summary")
def daily_checkin_summary_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["daily_checkin_summary"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("daily_checkin_summary", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/daily_checkin_summary/{item_id}")
def daily_checkin_summary_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("daily_checkin_summary", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/daily_checkin_summary/{item_id}")
async def daily_checkin_summary_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "daily_checkin_summary", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "daily_checkin_summary", 'result': result}


@router.delete("/daily_checkin_summary/{item_id}")
async def daily_checkin_summary_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "daily_checkin_summary", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "daily_checkin_summary", 'result': result}


# --- audit_trail (kernel execute_action template) ---


def _audit_trail_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.audit_trail import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/audit_trail")
async def audit_trail_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("audit_trail", payload)
    CAPABILITY_ID = "audit_trail"
    handle = _audit_trail_handle
    save = lambda record: store.save("audit_trail", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("audit_trail", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'actor', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'actor': {'required': True}, 'change_type': {'allowed_values': ['create', 'update', 'delete'], 'required': False}, 'subject_capability': {'required': False}, 'changed_at': {'format': 'datetime', 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    for name, rules in constraints.items():
        if name not in payload:
            continue
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            return {"ok": False,
                    "error": name + " must be one of: " + ", ".join(allowed)}
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if low is not None and value < low:
            return {"ok": False, "error": name + " is below the minimum"}
        if high is not None and value > high:
            return {"ok": False, "error": name + " is above the maximum"}
    result = await run_capability(CAPABILITY_ID, payload, request)
    if isinstance(result, dict) and result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    try:
        stored = save(payload)
    except Exception as exc:
        return {'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'capability': CAPABILITY_ID}
    return {"ok": True, "capability": CAPABILITY_ID, "result": result,
            "stored": stored}


@router.get("/audit_trail")
def audit_trail_list(request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["audit_trail"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("audit_trail", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/audit_trail/{item_id}")
def audit_trail_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import read_tenant
    tenant = read_tenant(request)
    record = store.get("audit_trail", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/audit_trail/{item_id}")
async def audit_trail_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "audit_trail", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "audit_trail", 'result': result}


@router.delete("/audit_trail/{item_id}")
async def audit_trail_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "audit_trail", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "audit_trail", 'result': result}


@router.post("/work_queue")
async def work_queue_enqueue(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    result = await perform_domain(
        "enqueue", str((payload or {}).get("capability_id") or ""), payload or {}
    )
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'result': result}


@router.post("/work_queue/{item_id}/process")
async def work_queue_process(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    result = await perform_domain("process", "", {"id": item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'result': result}


@router.get("/work_queue")
def work_queue_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app import work_queue as _work_queue
    return {"items": _work_queue.list_all()}



# --- platform surfaces the capabilities actually use -----------------------


@router.get("/vendor_health")
def vendor_health(request: Request) -> Dict[str, Any]:
    """Live loadability of every vendored block this platform binds."""
    import importlib

    from app.auth import require_platform_token
    from app.vendor_health import report

    require_platform_token(request)
    bound: List[str] = []
    for item in jobs.CAPABILITIES:
        name = str(item.get("id") or "").replace("-", "_")
        if not name:
            continue
        try:
            module = importlib.import_module("app.actions." + name)
        except ImportError:
            continue
        for block_id in getattr(module, "BLOCK_IDS", ()) or ():
            if str(block_id) and str(block_id) not in bound:
                bound.append(str(block_id))
    return report(sorted(bound))


@router.get("/tenancy")
def tenancy_binding(request: Request) -> Dict[str, Any]:
    """Who the caller is, and which tenant the platform bound for the request."""
    from app.security import fingerprint, require_principal

    principal = require_principal(request)
    return {
        "principal": principal.to_dict(),
        "tenant": principal.tenant,
        "tenant_source": "authenticated principal",
        "roles": list(principal.roles),
        "token_fingerprint": fingerprint(principal.token),
    }


@router.post("/corpus/documents")
async def corpus_ingest(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Ingest one document into the bound tenant's corpus."""
    from app import retrieval
    from app.security import require_principal

    principal = require_principal(request)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    try:
        stored = retrieval.ingest(
            tenant=principal.tenant,
            title=str(payload.get("title") or ""),
            body=str(payload.get("body") or ""),
            source_kind=str(payload.get("source_kind") or "document"),
            certified=bool(payload.get("certified")),
            version=str(payload.get("version") or "1.0.0"),
        )
    except retrieval.CorpusRefused as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "tenant": principal.tenant, "stored": stored}


@router.get("/corpus/documents")
def corpus_list(request: Request) -> Dict[str, Any]:
    """This tenant's documents only."""
    from app import retrieval
    from app.security import require_principal

    principal = require_principal(request)
    body = retrieval.list_documents(principal.tenant)
    return {"ok": True, "tenant": principal.tenant, "items": body["items"], "total": body["total"]}


@router.get("/answers")
def grounded_answer(request: Request) -> Dict[str, Any]:
    """Answer a question from the bound tenant's corpus, with precedence labels."""
    from app import llm
    from app.security import require_principal

    principal = require_principal(request)
    question = str(request.query_params.get("q") or "").strip()
    if not question:
        return {"ok": False, "error": "q is required"}
    try:
        limit = int(request.query_params.get("limit") or 5)
    except ValueError:
        return {"ok": False, "error": "limit must be an integer"}
    return {"ok": True, **llm.answer(question, tenant=principal.tenant, limit=limit)}


@router.get("/precedence")
def precedence_table(request: Request) -> Dict[str, Any]:
    """precedence.v1 as data: 1 certified > 2 documents > 3 formulas > 4 procedures."""
    from app import authority
    from app.auth import require_platform_token

    require_platform_token(request)
    return authority.declaration()


@router.get("/formulas")
def formula_registry(request: Request) -> Dict[str, Any]:
    """The versioned formula registry (precedence layer 3)."""
    from app import formulas
    from app.auth import require_platform_token

    require_platform_token(request)
    return formulas.declaration()


@router.get("/llm")
def llm_status(request: Request) -> Dict[str, Any]:
    """What the answer adapter really is: offline and deterministic."""
    from app import llm
    from app.auth import require_platform_token

    require_platform_token(request)
    return llm.status()
