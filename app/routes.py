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

#: Which authority layer produced a capability's answer. Persisted operator
#: records are procedure-layer data; the quoting and rollup capabilities
#: answer with app/formulas, which is the formula layer.
_FORMULA_LAYER_CAPABILITIES = (
    "pricing_and_rate_cards",
    "invoicing_and_deposits",
    "multi_branch_rollup",
    "reporting_analytics",
)


def authority_label(capability_id: str) -> Dict[str, Any]:
    """The per-answer authority label (precedence.v1) for one capability."""
    from app.authority import claim_label

    layer = (
        "formulas"
        if str(capability_id) in _FORMULA_LAYER_CAPABILITIES
        else "procedures"
    )
    return {**claim_label(layer), "capability": str(capability_id)}



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


@router.get("/settings")
def settings_summary(request: Request) -> Dict[str, Any]:
    """Which operator settings are set, and which are still owed.

    Names only — never a secret's value. Country, currency and every tax
    rate are the customer's to supply; the platform invents none of them.
    """
    from app.auth import require_platform_token
    from app.settings import summary

    require_platform_token(request)
    return dict(summary())


@router.get("/schema")
def schema(request: Request) -> Dict[str, Any]:
    """The capability models' own field vocabulary, for the staff console.

    The UI reads the field list from here instead of carrying a second,
    drifting copy of the schema. Tenant-scoped surface, so it needs a token
    like every other data-bearing route.
    """
    from app.auth import require_platform_token
    from app.models import MODELS

    require_platform_token(request)
    return {
        "capabilities": {
            name: {
                "entity": name,
                "fields": list(getattr(model, "FIELDS", []) or []),
                "constraints": dict(getattr(model, "CONSTRAINTS", {}) or {}),
            }
            for name, model in sorted(MODELS.items())
        }
    }


# --- fleet_registry (kernel execute_action template) ---


def _fleet_registry_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.fleet_registry import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/fleet_registry")
async def fleet_registry_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("fleet_registry", payload)
    CAPABILITY_ID = "fleet_registry"
    handle = _fleet_registry_handle
    save = lambda record: store.save("fleet_registry", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("fleet_registry", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'audit', 'database', 'storage']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'mileage': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
            "stored": stored,
            "authority": authority_label(CAPABILITY_ID)}


@router.get("/fleet_registry")
def fleet_registry_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["fleet_registry"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("fleet_registry", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/fleet_registry/{item_id}")
def fleet_registry_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("fleet_registry", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {**record, "authority": authority_label("fleet_registry")}


@router.put("/fleet_registry/{item_id}")
async def fleet_registry_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "fleet_registry", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "fleet_registry", 'result': result}


@router.delete("/fleet_registry/{item_id}")
async def fleet_registry_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "fleet_registry", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "fleet_registry", 'result': result}


# --- rental_contract_management (kernel execute_action template) ---


def _rental_contract_management_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.rental_contract_management import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/rental_contract_management")
async def rental_contract_management_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("rental_contract_management", payload)
    CAPABILITY_ID = "rental_contract_management"
    handle = _rental_contract_management_handle
    save = lambda record: store.save("rental_contract_management", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("rental_contract_management", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'pickup_date': {'format': 'date'}, 'return_date': {'format': 'date'}, 'extension_days': {'min': 0}, 'daily_rate': {'min': 0}, 'deposit_amount': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
            "stored": stored,
            "authority": authority_label(CAPABILITY_ID)}


@router.get("/rental_contract_management")
def rental_contract_management_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["rental_contract_management"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("rental_contract_management", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/rental_contract_management/{item_id}")
def rental_contract_management_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("rental_contract_management", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {**record, "authority": authority_label("rental_contract_management")}


@router.put("/rental_contract_management/{item_id}")
async def rental_contract_management_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "rental_contract_management", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "rental_contract_management", 'result': result}


@router.delete("/rental_contract_management/{item_id}")
async def rental_contract_management_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "rental_contract_management", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "rental_contract_management", 'result': result}


# --- maintenance_scheduling (kernel execute_action template) ---


def _maintenance_scheduling_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.maintenance_scheduling import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/maintenance_scheduling")
async def maintenance_scheduling_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("maintenance_scheduling", payload)
    CAPABILITY_ID = "maintenance_scheduling"
    handle = _maintenance_scheduling_handle
    save = lambda record: store.save("maintenance_scheduling", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("maintenance_scheduling", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['title', 'reference', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'title': {'required': True}, 'schedule_kind': {'allowed_values': ['date', 'mileage']}, 'due_date': {'format': 'date'}, 'due_mileage': {'min': 0}, 'downtime_days': {'min': 0}, 'estimated_cost': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
            "stored": stored,
            "authority": authority_label(CAPABILITY_ID)}


@router.get("/maintenance_scheduling")
def maintenance_scheduling_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["maintenance_scheduling"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("maintenance_scheduling", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/maintenance_scheduling/{item_id}")
def maintenance_scheduling_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("maintenance_scheduling", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {**record, "authority": authority_label("maintenance_scheduling")}


@router.put("/maintenance_scheduling/{item_id}")
async def maintenance_scheduling_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "maintenance_scheduling", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "maintenance_scheduling", 'result': result}


@router.delete("/maintenance_scheduling/{item_id}")
async def maintenance_scheduling_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "maintenance_scheduling", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "maintenance_scheduling", 'result': result}


# --- pricing_and_rate_cards (kernel execute_action template) ---


def _pricing_and_rate_cards_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.pricing_and_rate_cards import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/pricing_and_rate_cards")
async def pricing_and_rate_cards_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("pricing_and_rate_cards", payload)
    CAPABILITY_ID = "pricing_and_rate_cards"
    handle = _pricing_and_rate_cards_handle
    save = lambda record: store.save("pricing_and_rate_cards", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("pricing_and_rate_cards", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'analytics', 'audit', 'formula_executor', 'validation']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'duration_days': {'min': 1}, 'base_rate': {'min': 0}, 'mileage_charge': {'min': 0}, 'fuel_charge': {'min': 0}, 'late_return_charge': {'min': 0}, 'extras_charge': {'min': 0}, 'deposit_amount': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
            "stored": stored,
            "authority": authority_label(CAPABILITY_ID)}


@router.get("/pricing_and_rate_cards")
def pricing_and_rate_cards_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["pricing_and_rate_cards"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("pricing_and_rate_cards", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/pricing_and_rate_cards/{item_id}")
def pricing_and_rate_cards_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("pricing_and_rate_cards", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {**record, "authority": authority_label("pricing_and_rate_cards")}


@router.put("/pricing_and_rate_cards/{item_id}")
async def pricing_and_rate_cards_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "pricing_and_rate_cards", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "pricing_and_rate_cards", 'result': result}


@router.delete("/pricing_and_rate_cards/{item_id}")
async def pricing_and_rate_cards_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "pricing_and_rate_cards", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "pricing_and_rate_cards", 'result': result}


# --- invoicing_and_deposits (kernel execute_action template) ---


def _invoicing_and_deposits_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.invoicing_and_deposits import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/invoicing_and_deposits")
async def invoicing_and_deposits_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("invoicing_and_deposits", payload)
    CAPABILITY_ID = "invoicing_and_deposits"
    handle = _invoicing_and_deposits_handle
    save = lambda record: store.save("invoicing_and_deposits", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("invoicing_and_deposits", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'analytics', 'audit', 'database', 'workflow']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'amount_due': {'min': 0}, 'deposit_held': {'min': 0}, 'balance_due': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
            "stored": stored,
            "authority": authority_label(CAPABILITY_ID)}


@router.get("/invoicing_and_deposits")
def invoicing_and_deposits_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["invoicing_and_deposits"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("invoicing_and_deposits", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/invoicing_and_deposits/{item_id}")
def invoicing_and_deposits_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("invoicing_and_deposits", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {**record, "authority": authority_label("invoicing_and_deposits")}


@router.put("/invoicing_and_deposits/{item_id}")
async def invoicing_and_deposits_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "invoicing_and_deposits", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "invoicing_and_deposits", 'result': result}


@router.delete("/invoicing_and_deposits/{item_id}")
async def invoicing_and_deposits_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "invoicing_and_deposits", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "invoicing_and_deposits", 'result': result}


# --- multi_branch_rollup (kernel execute_action template) ---


def _multi_branch_rollup_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.multi_branch_rollup import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/multi_branch_rollup")
async def multi_branch_rollup_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("multi_branch_rollup", payload)
    CAPABILITY_ID = "multi_branch_rollup"
    handle = _multi_branch_rollup_handle
    save = lambda record: store.save("multi_branch_rollup", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("multi_branch_rollup", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'analytics', 'dashboard', 'estate_registry', 'portfolio_rollup']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'fleet_utilisation': {'min': 0, 'max': 100}, 'revenue': {'min': 0}, 'cost': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
            "stored": stored,
            "authority": authority_label(CAPABILITY_ID)}


@router.get("/multi_branch_rollup")
def multi_branch_rollup_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["multi_branch_rollup"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("multi_branch_rollup", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/multi_branch_rollup/{item_id}")
def multi_branch_rollup_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("multi_branch_rollup", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {**record, "authority": authority_label("multi_branch_rollup")}


@router.put("/multi_branch_rollup/{item_id}")
async def multi_branch_rollup_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "multi_branch_rollup", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "multi_branch_rollup", 'result': result}


@router.delete("/multi_branch_rollup/{item_id}")
async def multi_branch_rollup_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "multi_branch_rollup", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "multi_branch_rollup", 'result': result}


# --- reporting_analytics (kernel execute_action template) ---


def _reporting_analytics_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.reporting_analytics import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/reporting_analytics")
async def reporting_analytics_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    tenant = require_platform_token(request)
    reject_invalid_payload("reporting_analytics", payload)
    CAPABILITY_ID = "reporting_analytics"
    handle = _reporting_analytics_handle
    save = lambda record: store.save("reporting_analytics", record, tenant_id=tenant.tenant_id)
    list_all = lambda: store.list_all("reporting_analytics", tenant_id=tenant.tenant_id)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'status', 'analytics', 'dashboard', 'memory', 'vector_search']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'value': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
            "stored": stored,
            "authority": authority_label(CAPABILITY_ID)}


@router.get("/reporting_analytics")
def reporting_analytics_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["reporting_analytics"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("reporting_analytics", tenant.tenant_id,
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/reporting_analytics/{item_id}")
def reporting_analytics_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("reporting_analytics", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {**record, "authority": authority_label("reporting_analytics")}


@router.put("/reporting_analytics/{item_id}")
async def reporting_analytics_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("update", "reporting_analytics", {**(payload or {}), 'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "reporting_analytics", 'result': result}


@router.delete("/reporting_analytics/{item_id}")
async def reporting_analytics_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    from app.kernel_bridge import product_context
    result = await perform_domain("delete", "reporting_analytics", {'id': item_id}, context=product_context(request))
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "reporting_analytics", 'result': result}


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
    required_fields = ['reference', 'status', 'audit', 'capture', 'evidence_verifier', 'file_hasher']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
            "stored": stored,
            "authority": authority_label(CAPABILITY_ID)}


@router.get("/audit_trail")
def audit_trail_list(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
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
    from app.auth import require_platform_token
    tenant = require_platform_token(request)
    record = store.get("audit_trail", item_id, tenant.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return {**record, "authority": authority_label("audit_trail")}


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

