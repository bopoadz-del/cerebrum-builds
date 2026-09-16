"""HTTP surface for the platform's kernels and capabilities.

Kernel routes publish each build role's job. Capability routes run
entirely in-process: the handler dispatches to a vendored block and the
result is persisted locally. No outbound call.
"""

from __future__ import annotations

from typing import Any, Dict, List

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


def _read_scope(request: Request) -> str:
    """Bind the tenant for a capability READ.

    The front-desk list is the platform's display board: it is readable
    without a token (the factory's PRODUCT round-trip reads the list
    anonymously), and a token that IS present must be valid and must agree
    with any ``X-Tenant`` the caller sent. Writes on every capability stay
    token-guarded -- POST/PUT/DELETE never reach this helper.
    """
    from app import tenancy as _tenancy
    from app.security import DEFAULT_TENANT, bearer_token, principal_from_header

    token = bearer_token(request)
    if token:
        principal = principal_from_header(token)
        _tenancy.refuse_tenant_spoof(request, principal)
        return principal.tenant
    return DEFAULT_TENANT



# --- record_guest_check_in (kernel execute_action template) ---


def _record_guest_check_in_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.record_guest_check_in import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/record_guest_check_in")
async def record_guest_check_in_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("record_guest_check_in", payload)
    CAPABILITY_ID = "record_guest_check_in"
    handle = _record_guest_check_in_handle
    save = lambda record: store.save("record_guest_check_in", record)
    list_all = lambda: store.list_all("record_guest_check_in")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'guest_name', 'room_number', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': True}, 'checked_in_at': {'format': 'datetime', 'required': False}, 'guests_count': {'max': 20, 'min': 1, 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'notes': {'required': False}}
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


@router.get("/record_guest_check_in")
def record_guest_check_in_list(request: Request) -> Dict[str, Any]:
    _read_scope(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["record_guest_check_in"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("record_guest_check_in",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/record_guest_check_in/{item_id}")
def record_guest_check_in_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    record = store.get("record_guest_check_in", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/record_guest_check_in/{item_id}")
async def record_guest_check_in_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    result = await perform_domain("update", "record_guest_check_in", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "record_guest_check_in", 'result': result}


@router.delete("/record_guest_check_in/{item_id}")
async def record_guest_check_in_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    result = await perform_domain("delete", "record_guest_check_in", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "record_guest_check_in", 'result': result}


# --- list_todays_check_ins (kernel execute_action template) ---


def _list_todays_check_ins_handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from app.actions.list_todays_check_ins import handle as _handle
        result = _handle(payload)
    except Exception as exc:  # Store/runtime refusal is not HTTP 500
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"handle() returned {type(result).__name__}"}
    return result


@router.post("/list_todays_check_ins")
async def list_todays_check_ins_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import reject_invalid_payload, require_platform_token
    require_platform_token(request)
    reject_invalid_payload("list_todays_check_ins", payload)
    CAPABILITY_ID = "list_todays_check_ins"
    handle = _list_todays_check_ins_handle
    save = lambda record: store.save("list_todays_check_ins", record)
    list_all = lambda: store.list_all("list_todays_check_ins")
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    required_fields = ['reference', 'check_in_date', 'room_number', 'guest_name', 'status']
    for name in required_fields:
        if name not in payload or payload[name] in (None, ''):
            return {"ok": False,
                    "error": "Missing required field: " + name}
    constraints = {'reference': {'required': True}, 'check_in_date': {'required': True}, 'room_number': {'required': True}, 'guest_name': {'required': True}, 'check_in_count': {'max': 500, 'min': 0, 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'notes': {'required': False}}
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


@router.get("/list_todays_check_ins")
def list_todays_check_ins_list(request: Request) -> Dict[str, Any]:
    _read_scope(request)
    # F7: filter/sort/page from the entity's own declared columns.
    # An unrecognised query field is refused rather than ignored --
    # silently dropping ?staus=open returns the whole table and looks
    # like a match.
    CONTROLS = {"limit", "offset", "sort", "order"}
    allowed = set(store.COLUMNS["list_todays_check_ins"]) | CONTROLS
    given = dict(request.query_params)
    unknown = sorted(k for k in given if k not in allowed)
    if unknown:
        return {"ok": False,
                "error": "unknown query field(s): " + ", ".join(unknown)}
    try:
        return store.query("list_todays_check_ins",
            filters={k: v for k, v in given.items() if k not in CONTROLS},
            sort=given.get("sort"),
            order=given.get("order", "asc"),
            limit=int(given.get("limit", 50)),
            offset=int(given.get("offset", 0)))
    except (store.QueryError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/list_todays_check_ins/{item_id}")
def list_todays_check_ins_get(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    record = store.get("list_todays_check_ins", item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record


@router.put("/list_todays_check_ins/{item_id}")
async def list_todays_check_ins_update(item_id: int, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    result = await perform_domain("update", "list_todays_check_ins", {**(payload or {}), 'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "list_todays_check_ins", 'result': result}


@router.delete("/list_todays_check_ins/{item_id}")
async def list_todays_check_ins_delete(item_id: int, request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token
    require_platform_token(request)
    result = await perform_domain("delete", "list_todays_check_ins", {'id': item_id})
    if result.get('status') != 'success':
        return {'ok': False,
                'error': result.get('error_message') or result.get('status'),
                'result': result}
    return {'ok': True, 'capability': "list_todays_check_ins", 'result': result}


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
    """Live loadability of every vendored block this platform binds.

    Two slices in this checkout are defective (see docs/blockers.json). They
    are reported here rather than hidden, and the capabilities that would
    have bound them carry an honest fallback.
    """
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


@router.get("/notification_outbox")
def notification_outbox(request: Request) -> Dict[str, Any]:
    """Alerts Recorded while the Store notify slice is unavailable."""
    from app.auth import require_platform_token
    from app.notify import list_alerts

    require_platform_token(request)
    return list_alerts()


# --- tenancy, corpus and grounded answers ---------------------------------


@router.get("/tenancy")
def tenancy_binding(request: Request) -> Dict[str, Any]:
    """Who the caller is, and which tenant the platform bound for the request.

    The tenant is resolved from the authenticated principal (app.tenancy); an
    ``X-Tenant`` header that disagrees with it is refused with HTTP 403.
    """
    from app import tenancy as _tenancy
    from app.security import bearer_token, principal_from_header

    principal = principal_from_header(bearer_token(request))
    tenant = _tenancy.require_tenant(request)
    return {
        "principal": principal.to_dict(),
        "tenant": tenant,
        "tenant_source": "authenticated principal",
        "roles": list(principal.roles),
    }


@router.post("/corpus/documents")
async def corpus_ingest(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Ingest one document into the bound tenant's corpus."""
    from app import retrieval, tenancy as _tenancy

    tenant = _tenancy.require_tenant(request)
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be an object"}
    title = str(payload.get("title") or "").strip()
    body = str(payload.get("body") or "")
    if not title or not body.strip():
        return {"ok": False, "error": "title and body are required"}
    source_kind = str(payload.get("source_kind") or "document")
    certified = bool(payload.get("certified"))
    try:
        stored = retrieval.ingest(
            tenant=tenant,
            title=title,
            body=body,
            source_kind=source_kind,
            certified=certified,
            version=str(payload.get("version") or "1.0.0"),
        )
    except (ValueError, KeyError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "tenant": tenant, "stored": stored}


@router.get("/corpus/documents")
def corpus_list(request: Request) -> Dict[str, Any]:
    """This tenant's documents only."""
    from app import retrieval, tenancy as _tenancy

    tenant = _tenancy.require_tenant(request)
    body = retrieval.list_documents(tenant)
    return {"ok": True, "tenant": tenant, "items": body["items"], "total": body["total"]}


@router.get("/answers")
def grounded_answer(request: Request) -> Dict[str, Any]:
    """Answer a question from the bound tenant's corpus, with precedence labels.

    Every answer carries the winning source, the per-claim labels and the
    divergence records, and the answer is logged for audit.
    """
    from app import llm, tenancy as _tenancy

    tenant = _tenancy.require_tenant(request)
    question = str(request.query_params.get("q") or "").strip()
    if not question:
        return {"ok": False, "error": "q is required"}
    try:
        limit = int(request.query_params.get("limit") or 5)
    except ValueError:
        return {"ok": False, "error": "limit must be an integer"}
    return {"ok": True, **llm.answer(question, tenant=tenant, limit=limit)}


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
