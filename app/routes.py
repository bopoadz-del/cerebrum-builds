"""HTTP surface for the platform's kernels and capabilities.

Kernel routes publish each build role's job. Capability routes run
entirely in-process: the handler dispatches to a vendored block and
the result is persisted locally. No outbound call.

Written by the factory WRITER role (codewhale exec)
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


# --- inventory_management (kernel execute_action template) ---


def _inventory_management_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.inventory_management import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/inventory_management")
async def inventory_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("inventory_management", payload)
    CAPABILITY_ID = "inventory_management"
    handle = _inventory_management_handle
    save = lambda record: store.save("inventory_management", record)
    list_all = lambda: store.list_all("inventory_management")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'sku', 'product_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'sku': {'required': True}, 'product_name': {'required': True}, 'location': {'required': False}, 'quantity_on_hand': {'min': 0, 'max': 100000, 'required': False}, 'reorder_point': {'min': 0, 'max': 100000, 'required': False}, 'unit_cost': {'min': 0.0, 'max': 100000.0, 'required': False}, 'supplier_name': {'required': False}, 'category': {'required': False}, 'movement_type': {'required': False}, 'last_counted_date': {'format': 'date', 'required': False}}
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


@router.get("/inventory_management")
def inventory_management_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["inventory_management"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("inventory_management",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/inventory_management/{item_id}")
def inventory_management_get(item_id: int) -> Dict[str, Any]:
    record = store.get("inventory_management", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/inventory_management/{item_id}")
async def inventory_management_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "inventory_management", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "inventory_management", 'result': result}


@router.delete("/inventory_management/{item_id}")
async def inventory_management_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "inventory_management", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "inventory_management", 'result': result}


# --- sales_and_orders (kernel execute_action template) ---


def _sales_and_orders_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.sales_and_orders import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/sales_and_orders")
async def sales_and_orders_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("sales_and_orders", payload)
    CAPABILITY_ID = "sales_and_orders"
    handle = _sales_and_orders_handle
    save = lambda record: store.save("sales_and_orders", record)
    list_all = lambda: store.list_all("sales_and_orders")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'order_number', 'customer_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'order_number': {'required': True}, 'customer_name': {'required': True}, 'customer_email': {'required': False}, 'channel': {'required': False}, 'order_total': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'item_count': {'min': 0, 'max': 100000, 'required': False}, 'payment_status': {'required': False}, 'fulfilment_status': {'required': False}, 'order_date': {'format': 'date', 'required': False}, 'notes': {'required': False}}
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


@router.get("/sales_and_orders")
def sales_and_orders_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["sales_and_orders"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("sales_and_orders",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/sales_and_orders/{item_id}")
def sales_and_orders_get(item_id: int) -> Dict[str, Any]:
    record = store.get("sales_and_orders", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/sales_and_orders/{item_id}")
async def sales_and_orders_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "sales_and_orders", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "sales_and_orders", 'result': result}


@router.delete("/sales_and_orders/{item_id}")
async def sales_and_orders_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "sales_and_orders", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "sales_and_orders", 'result': result}


# --- customer_insights (kernel execute_action template) ---


def _customer_insights_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.customer_insights import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/customer_insights")
async def customer_insights_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("customer_insights", payload)
    CAPABILITY_ID = "customer_insights"
    handle = _customer_insights_handle
    save = lambda record: store.save("customer_insights", record)
    list_all = lambda: store.list_all("customer_insights")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'customer_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'customer_name': {'required': True}, 'customer_email': {'required': False}, 'segment': {'required': False}, 'lifetime_value': {'min': 0.0, 'max': 10000000.0, 'required': False}, 'orders_count': {'min': 0, 'max': 1000000, 'required': False}, 'last_purchase_date': {'format': 'date', 'required': False}, 'loyalty_tier': {'required': False}, 'preferred_channel': {'required': False}, 'insight_summary': {'required': False}, 'tags': {'required': False}}
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


@router.get("/customer_insights")
def customer_insights_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["customer_insights"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("customer_insights",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/customer_insights/{item_id}")
def customer_insights_get(item_id: int) -> Dict[str, Any]:
    record = store.get("customer_insights", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/customer_insights/{item_id}")
async def customer_insights_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "customer_insights", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "customer_insights", 'result': result}


@router.delete("/customer_insights/{item_id}")
async def customer_insights_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "customer_insights", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "customer_insights", 'result': result}


# --- analytics_dashboard (kernel execute_action template) ---


def _analytics_dashboard_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.analytics_dashboard import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/analytics_dashboard")
async def analytics_dashboard_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("analytics_dashboard", payload)
    CAPABILITY_ID = "analytics_dashboard"
    handle = _analytics_dashboard_handle
    save = lambda record: store.save("analytics_dashboard", record)
    list_all = lambda: store.list_all("analytics_dashboard")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'dashboard_name', 'metric_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'dashboard_name': {'required': True}, 'metric_name': {'required': True}, 'metric_value': {'min': 0.0, 'max': 100000000.0, 'required': False}, 'period_start': {'format': 'date', 'required': False}, 'period_end': {'format': 'date', 'required': False}, 'store_location': {'required': False}, 'widget_type': {'required': False}, 'report_format': {'required': False}, 'owner': {'required': False}, 'generated_at': {'format': 'datetime', 'required': False}}
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


@router.get("/analytics_dashboard")
def analytics_dashboard_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["analytics_dashboard"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("analytics_dashboard",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/analytics_dashboard/{item_id}")
def analytics_dashboard_get(item_id: int) -> Dict[str, Any]:
    record = store.get("analytics_dashboard", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/analytics_dashboard/{item_id}")
async def analytics_dashboard_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "analytics_dashboard", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "analytics_dashboard", 'result': result}


@router.delete("/analytics_dashboard/{item_id}")
async def analytics_dashboard_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "analytics_dashboard", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "analytics_dashboard", 'result': result}


# --- supplier_and_purchasing (kernel execute_action template) ---


def _supplier_and_purchasing_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.supplier_and_purchasing import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/supplier_and_purchasing")
async def supplier_and_purchasing_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("supplier_and_purchasing", payload)
    CAPABILITY_ID = "supplier_and_purchasing"
    handle = _supplier_and_purchasing_handle
    save = lambda record: store.save("supplier_and_purchasing", record)
    list_all = lambda: store.list_all("supplier_and_purchasing")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'supplier_name', 'purchase_order_number']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'supplier_name': {'required': True}, 'supplier_email': {'required': False}, 'purchase_order_number': {'required': True}, 'sku': {'required': False}, 'quantity_ordered': {'min': 0, 'max': 100000, 'required': False}, 'unit_cost': {'min': 0.0, 'max': 100000.0, 'required': False}, 'lead_time_days': {'min': 0, 'max': 365, 'required': False}, 'order_date': {'format': 'date', 'required': False}, 'expected_date': {'format': 'date', 'required': False}, 'payment_terms': {'required': False}}
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


@router.get("/supplier_and_purchasing")
def supplier_and_purchasing_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["supplier_and_purchasing"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("supplier_and_purchasing",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/supplier_and_purchasing/{item_id}")
def supplier_and_purchasing_get(item_id: int) -> Dict[str, Any]:
    record = store.get("supplier_and_purchasing", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/supplier_and_purchasing/{item_id}")
async def supplier_and_purchasing_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "supplier_and_purchasing", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "supplier_and_purchasing", 'result': result}


@router.delete("/supplier_and_purchasing/{item_id}")
async def supplier_and_purchasing_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "supplier_and_purchasing", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "supplier_and_purchasing", 'result': result}


# --- omnichannel_integration (kernel execute_action template) ---


def _omnichannel_integration_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.omnichannel_integration import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/omnichannel_integration")
async def omnichannel_integration_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("omnichannel_integration", payload)
    CAPABILITY_ID = "omnichannel_integration"
    handle = _omnichannel_integration_handle
    save = lambda record: store.save("omnichannel_integration", record)
    list_all = lambda: store.list_all("omnichannel_integration")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'integration_name']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'integration_name': {'required': True}, 'channel': {'required': False}, 'external_order_id': {'required': False}, 'sync_direction': {'required': False}, 'sync_status': {'required': False}, 'sku': {'required': False}, 'quantity': {'min': 0, 'max': 100000, 'required': False}, 'sync_at': {'format': 'datetime', 'required': False}, 'marketplace': {'required': False}, 'notes': {'required': False}}
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


@router.get("/omnichannel_integration")
def omnichannel_integration_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["omnichannel_integration"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("omnichannel_integration",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/omnichannel_integration/{item_id}")
def omnichannel_integration_get(item_id: int) -> Dict[str, Any]:
    record = store.get("omnichannel_integration", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/omnichannel_integration/{item_id}")
async def omnichannel_integration_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "omnichannel_integration", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "omnichannel_integration", 'result': result}


@router.delete("/omnichannel_integration/{item_id}")
async def omnichannel_integration_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "omnichannel_integration", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "omnichannel_integration", 'result': result}


# --- compliance_and_audit (kernel execute_action template) ---


def _compliance_and_audit_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.compliance_and_audit import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/compliance_and_audit")
async def compliance_and_audit_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("compliance_and_audit", payload)
    CAPABILITY_ID = "compliance_and_audit"
    handle = _compliance_and_audit_handle
    save = lambda record: store.save("compliance_and_audit", record)
    list_all = lambda: store.list_all("compliance_and_audit")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'control_id']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'control_id': {'required': True}, 'regulation': {'required': False}, 'event_type': {'required': False}, 'actor': {'required': False}, 'action_taken': {'required': False}, 'evidence_ref': {'required': False}, 'file_path': {'required': False}, 'findings': {'required': False}, 'occurred_at': {'format': 'datetime', 'required': False}, 'severity': {'required': False}}
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


@router.get("/compliance_and_audit")
def compliance_and_audit_list(request: Request) -> Dict[str, Any]:
    # F7: filter/sort/page from the entity's own declared columns.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["compliance_and_audit"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("compliance_and_audit",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/compliance_and_audit/{item_id}")
def compliance_and_audit_get(item_id: int) -> Dict[str, Any]:
    record = store.get("compliance_and_audit", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/compliance_and_audit/{item_id}")
async def compliance_and_audit_update(item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = await perform_domain("update", "compliance_and_audit", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "compliance_and_audit", 'result': result}


@router.delete("/compliance_and_audit/{item_id}")
async def compliance_and_audit_delete(item_id: int) -> Dict[str, Any]:
    result = await perform_domain("delete", "compliance_and_audit", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "compliance_and_audit", 'result': result}

