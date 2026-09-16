"""HTTP surface for the platform's kernels and capabilities.

Kernel routes publish each build role's job. Capability routes run
entirely in-process: the handler dispatches to a vendored block and
the result is persisted locally. No outbound call.
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


# --- matter_management (kernel execute_action template) ---


def _matter_management_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.matter_management import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/matter_management")
async def matter_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("matter_management", payload)
    CAPABILITY_ID = "matter_management"
    handle = _matter_management_handle
    save = lambda record: store.save("matter_management", record)
    list_all = lambda: store.list_all("matter_management")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'matter_number', 'matter_title', 'client_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'matter_number': {'required': True}, 'matter_title': {'required': True}, 'client_name': {'required': True}, 'client_email': {'required': False}, 'practice_area': {'required': False}, 'responsible_attorney': {'required': False}, 'matter_stage': {'required': False}, 'priority': {'required': False}, 'opened_date': {'required': False}, 'deadline_date': {'required': False}, 'billing_type': {'required': False}, 'document_path': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/matter_management")
def matter_management_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["matter_management"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("matter_management",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/matter_management/{item_id}")
def matter_management_get(item_id: int) -> Dict[str, Any]:
    record = store.get("matter_management", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/matter_management/{item_id}")
async def matter_management_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "matter_management", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "matter_management", 'result': result}


@router.delete("/matter_management/{item_id}")
async def matter_management_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "matter_management", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "matter_management", 'result': result}


# --- client_intake (kernel execute_action template) ---


def _client_intake_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.client_intake import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/client_intake")
async def client_intake_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("client_intake", payload)
    CAPABILITY_ID = "client_intake"
    handle = _client_intake_handle
    save = lambda record: store.save("client_intake", record)
    list_all = lambda: store.list_all("client_intake")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'client_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'client_name': {'required': True}, 'client_email': {'required': False}, 'client_phone': {'required': False}, 'matter_type': {'required': False}, 'referral_source': {'required': False}, 'conflict_check': {'required': False}, 'risk_score': {'required': False}, 'estimated_fee': {'required': False}, 'retainer_amount': {'required': False}, 'document_path': {'required': False}, 'intake_date': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/client_intake")
def client_intake_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["client_intake"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("client_intake",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/client_intake/{item_id}")
def client_intake_get(item_id: int) -> Dict[str, Any]:
    record = store.get("client_intake", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/client_intake/{item_id}")
async def client_intake_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "client_intake", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "client_intake", 'result': result}


@router.delete("/client_intake/{item_id}")
async def client_intake_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "client_intake", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "client_intake", 'result': result}


# --- document_management (kernel execute_action template) ---


def _document_management_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.document_management import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/document_management")
async def document_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("document_management", payload)
    CAPABILITY_ID = "document_management"
    handle = _document_management_handle
    save = lambda record: store.save("document_management", record)
    list_all = lambda: store.list_all("document_management")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'document_title']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'document_title': {'required': True}, 'document_type': {'required': False}, 'matter_number': {'required': False}, 'version': {'required': False}, 'file_path': {'required': False}, 'content_hash': {'required': False}, 'confidentiality': {'required': False}, 'document_owner': {'required': False}, 'tags': {'required': False}, 'uploaded_by': {'required': False}, 'uploaded_at': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/document_management")
def document_management_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["document_management"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("document_management",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/document_management/{item_id}")
def document_management_get(item_id: int) -> Dict[str, Any]:
    record = store.get("document_management", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/document_management/{item_id}")
async def document_management_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "document_management", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "document_management", 'result': result}


@router.delete("/document_management/{item_id}")
async def document_management_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "document_management", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "document_management", 'result': result}


# --- time_and_billing (kernel execute_action template) ---


def _time_and_billing_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.time_and_billing import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/time_and_billing")
async def time_and_billing_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("time_and_billing", payload)
    CAPABILITY_ID = "time_and_billing"
    handle = _time_and_billing_handle
    save = lambda record: store.save("time_and_billing", record)
    list_all = lambda: store.list_all("time_and_billing")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'timekeeper', 'matter_number']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'timekeeper': {'required': True}, 'matter_number': {'required': True}, 'client_name': {'required': False}, 'client_email': {'required': False}, 'activity_date': {'required': False}, 'hours': {'min': 0.0, 'max': 1000.0, 'required': False}, 'hourly_rate': {'min': 0.0, 'max': 5000.0, 'required': False}, 'billable_amount': {'required': False}, 'invoice_number': {'required': False}, 'payment_status': {'required': False}, 'narrative': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/time_and_billing")
def time_and_billing_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["time_and_billing"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("time_and_billing",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/time_and_billing/{item_id}")
def time_and_billing_get(item_id: int) -> Dict[str, Any]:
    record = store.get("time_and_billing", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/time_and_billing/{item_id}")
async def time_and_billing_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "time_and_billing", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "time_and_billing", 'result': result}


@router.delete("/time_and_billing/{item_id}")
async def time_and_billing_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "time_and_billing", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "time_and_billing", 'result': result}


# --- client_portal (kernel execute_action template) ---


def _client_portal_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.client_portal import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/client_portal")
async def client_portal_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("client_portal", payload)
    CAPABILITY_ID = "client_portal"
    handle = _client_portal_handle
    save = lambda record: store.save("client_portal", record)
    list_all = lambda: store.list_all("client_portal")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'client_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'client_name': {'required': True}, 'client_email': {'required': False}, 'matter_number': {'required': False}, 'portal_access_level': {'required': False}, 'unread_messages': {'min': 0, 'max': 10000, 'required': False}, 'shared_documents': {'min': 0, 'max': 10000, 'required': False}, 'message_subject': {'required': False}, 'message_body': {'required': False}, 'last_login_at': {'required': False}, 'document_path': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/client_portal")
def client_portal_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["client_portal"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("client_portal",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/client_portal/{item_id}")
def client_portal_get(item_id: int) -> Dict[str, Any]:
    record = store.get("client_portal", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/client_portal/{item_id}")
async def client_portal_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "client_portal", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "client_portal", 'result': result}


@router.delete("/client_portal/{item_id}")
async def client_portal_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "client_portal", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "client_portal", 'result': result}


# --- legal_analytics (kernel execute_action template) ---


def _legal_analytics_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.legal_analytics import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/legal_analytics")
async def legal_analytics_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("legal_analytics", payload)
    CAPABILITY_ID = "legal_analytics"
    handle = _legal_analytics_handle
    save = lambda record: store.save("legal_analytics", record)
    list_all = lambda: store.list_all("legal_analytics")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'metric_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'metric_name': {'required': True}, 'metric_value': {'required': False}, 'benchmark_value': {'required': False}, 'practice_area': {'required': False}, 'dimension': {'required': False}, 'period_start': {'required': False}, 'period_end': {'required': False}, 'source_matter': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/legal_analytics")
def legal_analytics_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["legal_analytics"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("legal_analytics",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/legal_analytics/{item_id}")
def legal_analytics_get(item_id: int) -> Dict[str, Any]:
    record = store.get("legal_analytics", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/legal_analytics/{item_id}")
async def legal_analytics_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "legal_analytics", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "legal_analytics", 'result': result}


@router.delete("/legal_analytics/{item_id}")
async def legal_analytics_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "legal_analytics", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "legal_analytics", 'result': result}


# --- compliance_audit (kernel execute_action template) ---


def _compliance_audit_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.compliance_audit import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/compliance_audit")
async def compliance_audit_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("compliance_audit", payload)
    CAPABILITY_ID = "compliance_audit"
    handle = _compliance_audit_handle
    save = lambda record: store.save("compliance_audit", record)
    list_all = lambda: store.list_all("compliance_audit")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'control_id']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'control_id': {'required': True}, 'framework': {'required': False}, 'regulation': {'required': False}, 'event_type': {'required': False}, 'actor': {'required': False}, 'actor_role': {'required': False}, 'action_taken': {'required': False}, 'evidence_ref': {'required': False}, 'findings': {'required': False}, 'occurred_at': {'required': False}}
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
    result = await run_capability(CAPABILITY_ID, payload)
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


@router.get("/compliance_audit")
def compliance_audit_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["compliance_audit"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("compliance_audit",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/compliance_audit/{item_id}")
def compliance_audit_get(item_id: int) -> Dict[str, Any]:
    record = store.get("compliance_audit", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/compliance_audit/{item_id}")
async def compliance_audit_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "compliance_audit", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "compliance_audit", 'result': result}


@router.delete("/compliance_audit/{item_id}")
async def compliance_audit_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "compliance_audit", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "compliance_audit", 'result': result}
