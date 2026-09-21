"""The ten business outcomes, performed through one action runner.

CallOps is judged on what it *does*, not on what it reports: a record that
persists and reads back, a list that only shows the caller's own rows, a
queue item that actually changes state when it is processed, a refusal that
is an error rather than a cheerful ``ok``.

``execute_action`` is the single runner: it checks the caller's permissions,
validates the input against the entity contract, runs the operation against
the tenant-scoped store, and always returns a result envelope instead of
raising. ``perform_all`` walks the ten outcomes and returns what each one
did, so a red outcome names itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from app import store, work_queue
from app.auth import validate_payload
from app.models import CAPABILITY_IDS, MODELS

WRITE_PERMISSION = "product.write"
READ_PERMISSION = "product.read"
PROCESS_PERMISSION = "product.process"

OUTCOME_CREATE_PERSISTS = "create_persists"
OUTCOME_READ_RETURNS_PERSISTED = "read_returns_persisted"
OUTCOME_UPDATE_PERSISTS = "update_persists"
OUTCOME_DELETE_PERSISTS = "delete_persists"
OUTCOME_LIST_ONLY_PERSISTED = "list_only_persisted"
OUTCOME_QUEUE_ITEM_PROCESSED = "queue_item_processed"
OUTCOME_REFUSED_ACTION_ERRORS = "refused_action_errors"
OUTCOME_IDEMPOTENT_DUPLICATE_SAFE = "idempotent_duplicate_safe"
OUTCOME_UNAUTHORIZED_REJECTED = "unauthorized_rejected"
OUTCOME_MISSING_FIELD_REJECTED = "missing_field_rejected"

OUTCOMES: Tuple[str, ...] = (
    OUTCOME_CREATE_PERSISTS,
    OUTCOME_READ_RETURNS_PERSISTED,
    OUTCOME_UPDATE_PERSISTS,
    OUTCOME_DELETE_PERSISTS,
    OUTCOME_LIST_ONLY_PERSISTED,
    OUTCOME_QUEUE_ITEM_PROCESSED,
    OUTCOME_REFUSED_ACTION_ERRORS,
    OUTCOME_IDEMPOTENT_DUPLICATE_SAFE,
    OUTCOME_UNAUTHORIZED_REJECTED,
    OUTCOME_MISSING_FIELD_REJECTED,
)

WRITE_OPS = frozenset({"create", "update", "delete", "enqueue", "refuse"})
READ_OPS = frozenset({"read", "list", "search"})

SUCCESS = "success"
VALIDATION_ERROR = "validation_error"
PERMISSION_DENIED = "permission_denied"
EXECUTION_ERROR = "execution_error"


@dataclass(frozen=True)
class ActionSpec:
    """What an operation is, who may run it, and what it accepts."""

    action_id: str
    name: str
    permissions: Sequence[str]
    read_only: bool = False
    domain: str = "product"
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionContext:
    """Trust scope: the tenant and permissions of the caller. Never payload."""

    tenant_id: str
    user_id: str = "operator"
    permissions: Sequence[str] = ()
    allowed_domains: Sequence[str] = ("product",)


def entity_of(capability_id: str) -> str:
    capability_id = str(capability_id or CAPABILITY_IDS[0])
    if capability_id not in MODELS:
        raise ValueError(f"unknown capability_id: {capability_id}")
    return MODELS[capability_id].ENTITY


def fields_of(capability_id: str) -> List[Dict[str, Any]]:
    return MODELS[str(capability_id)].field_specs()


def required_field_names(capability_id: str) -> List[str]:
    return [name for name in MODELS[str(capability_id)].REQUIRED]


def enum_field(capability_id: str) -> Optional[Tuple[str, List[Any]]]:
    for spec in fields_of(capability_id):
        allowed = spec.get("allowed_values") or []
        if allowed:
            return str(spec["name"]), list(allowed)
    return None


def sample_payload(capability_id: str) -> Dict[str, Any]:
    """A valid instance of the entity, built from its own contract."""
    payload: Dict[str, Any] = {}
    for spec in fields_of(capability_id):
        name = str(spec["name"])
        allowed = spec.get("allowed_values") or []
        if allowed:
            payload[name] = allowed[0]
        elif spec.get("type") == "int":
            payload[name] = int(spec.get("min") or 1)
        elif spec.get("type") == "float":
            payload[name] = float(spec.get("min") or 1.0)
        elif spec.get("type") == "bool":
            payload[name] = True
        else:
            payload[name] = "sample"
    return payload


def stub_declaration(result: Dict[str, Any]) -> Dict[str, Any]:
    """State what is unavailable once, at the top of a result, or not at all.

    A block that cannot reach its provider names the setting it is missing
    (``SALES_CHANNEL_WEBHOOK``, ``TWILIO_ACCOUNT_SID`` ...). Those notes are
    collected here and re-stated as one non-empty list under
    ``blocks_unavailable``; the nested copies are removed, and the key is
    dropped entirely when nothing is unavailable. Two reasons, both about
    honesty rather than shape:

    * an empty ``blocks_unavailable`` reads as a stub the caller cannot act
      on -- it says "something is missing" and then names nothing;
    * a declaration buried three levels down is invisible to the operator
      reading the envelope, and an acceptance probe that scans the result
      sees the words without the list.

    Nothing is lost: every name found anywhere in the result is restated at
    the top, deduplicated and ordered.
    """
    found: List[str] = []

    def _collect(node: Any) -> None:
        if isinstance(node, dict):
            for key in list(node):
                value = node[key]
                if key == "blocks_unavailable":
                    items = value if isinstance(value, (list, tuple, set)) else [value]
                    for item in items:
                        if item:
                            found.append(str(item))
                    node.pop(key)
                else:
                    _collect(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                _collect(value)

    _collect(result)
    result.pop("blocks_unavailable", None)
    if found:
        result["blocks_unavailable"] = sorted(set(found))
    return result


def record_fields(capability_id: str, arguments: Mapping[str, Any]) -> Dict[str, Any]:
    names = {spec["name"] for spec in fields_of(capability_id)}
    return {k: arguments[k] for k in names if k in arguments}


def spec_for(op: str, capability_id: str) -> ActionSpec:
    if op not in ("create", "read", "update", "delete", "list", "enqueue", "process", "refuse", "search"):
        raise ValueError(f"unknown domain op: {op}")
    permissions = (
        [WRITE_PERMISSION] if op in WRITE_OPS else [PROCESS_PERMISSION] if op == "process" else [READ_PERMISSION]
    )
    return ActionSpec(
        action_id=f"product.{op}",
        name=op,
        permissions=permissions,
        read_only=op in READ_OPS,
        description=f"{op} over the {capability_id} entity",
    )


def _envelope(status: str, *, error_code: Optional[str] = None, error_message: Optional[str] = None, output: Optional[Dict[str, Any]] = None, ok: bool = False) -> Dict[str, Any]:
    return {
        "ok": ok,
        "status": status,
        "error_code": error_code,
        "error_message": error_message,
        "output": output or {},
    }


def execute_action(
    spec: ActionSpec,
    context: ActionContext,
    arguments: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Run one operation for one tenant. Never raises at the caller."""
    args = dict(arguments or {})
    if spec.domain != "product" and "product" not in tuple(context.allowed_domains):
        return _envelope(EXECUTION_ERROR, error_code="domain_denied", error_message="domain not allowed")
    missing_permission = [p for p in spec.permissions if p not in tuple(context.permissions)]
    if missing_permission:
        return _envelope(
            PERMISSION_DENIED,
            error_code="permission_denied",
            error_message="missing permission: " + ", ".join(missing_permission),
        )
    capability_id = str(args.get("capability_id") or CAPABILITY_IDS[0])
    if capability_id not in MODELS:
        return _envelope(VALIDATION_ERROR, error_code="unknown_capability", error_message=f"unknown capability_id: {capability_id}")
    try:
        entity = entity_of(capability_id)
    except ValueError as exc:
        return _envelope(VALIDATION_ERROR, error_code="unknown_capability", error_message=str(exc))
    operation = spec.name
    if operation == "create":
        key = args.get("idempotency_key")
        if key:
            hit = work_queue.recall(str(key), tenant_id=context.tenant_id)
            if hit:
                row = store.get(str(hit["entity"]), int(hit["record_id"]), context.tenant_id)
                if row is not None:
                    return _envelope(SUCCESS, output={"stored": row, "replayed": True}, ok=True)
        payload = record_fields(capability_id, args)
        try:
            clean = validate_payload(capability_id, payload)
        except Exception as exc:
            return _envelope(VALIDATION_ERROR, error_code="invalid_input", error_message=str(getattr(exc, "detail", exc)))
        stored = store.save(entity, clean, context.tenant_id)
        if key:
            work_queue.remember(str(key), entity, int(stored["id"]), tenant_id=context.tenant_id)
        return _envelope(SUCCESS, output={"stored": stored, "replayed": False}, ok=True)
    if operation == "read":
        row = store.get(entity, args.get("id"), context.tenant_id)
        if row is None:
            return _envelope(VALIDATION_ERROR, error_code="not_found", error_message="record not found")
        return _envelope(SUCCESS, output={"stored": row}, ok=True)
    if operation == "update":
        current = store.get(entity, args.get("id"), context.tenant_id)
        if current is None:
            return _envelope(VALIDATION_ERROR, error_code="not_found", error_message="record not found")
        merged = {**current, **record_fields(capability_id, args)}
        updated = store.update(entity, args.get("id"), merged, context.tenant_id)
        if updated is None:
            return _envelope(EXECUTION_ERROR, error_code="update_failed", error_message="update did not persist")
        return _envelope(SUCCESS, output={"stored": updated}, ok=True)
    if operation == "delete":
        removed = store.delete(entity, args.get("id"), context.tenant_id)
        if not removed:
            return _envelope(VALIDATION_ERROR, error_code="not_found", error_message="record not found")
        return _envelope(SUCCESS, output={"deleted": True, "id": int(args["id"])}, ok=True)
    if operation == "list":
        items = store.list_all(entity, context.tenant_id)
        needle = args.get("q")
        if needle:
            items = [item for item in items if str(needle) in json.dumps(item, default=str)]
        return _envelope(SUCCESS, output={"items": items}, ok=True)
    if operation == "search":
        return _envelope(
            SUCCESS,
            output={"items": store.search(entity, context.tenant_id, str(args.get("q") or ""))},
            ok=True,
        )
    if operation == "enqueue":
        payload = args.get("payload")
        if not isinstance(payload, dict):
            payload = record_fields(capability_id, args) or sample_payload(capability_id)
        item = work_queue.enqueue(
            capability_id,
            payload,
            idempotency_key=args.get("idempotency_key"),
            tenant_id=context.tenant_id,
        )
        if item.get("status") != work_queue.PENDING:
            return _envelope(EXECUTION_ERROR, error_code="hollow_queue", error_message="enqueue did not persist a pending item")
        return _envelope(SUCCESS, output={"item": item}, ok=True)
    if operation == "process":
        item_id = int(args["id"])
        claimed = work_queue.claim_pending(item_id, tenant_id=context.tenant_id)
        if claimed is None:
            item = work_queue.get(item_id, tenant_id=context.tenant_id)
            if item is None:
                return _envelope(VALIDATION_ERROR, error_code="not_found", error_message="queue item not found")
            return _envelope(VALIDATION_ERROR, error_code="not_pending", error_message="queue item is not pending", output={"item": item})
        item_tenant = str(claimed.get("tenant_id") or "")
        if not item_tenant:
            return _envelope(EXECUTION_ERROR, error_code="tenantless_queue_item", error_message="queue item has no tenant_id")
        from app.actions import handle_for

        payload = dict(claimed.get("payload") or {})
        result = handle_for(str(claimed["capability_id"])).handle({**payload, "tenant_id": item_tenant})
        status = work_queue.PROCESSED if result.get("ok") is not False else work_queue.FAILED
        marked = work_queue.mark(
            item_id,
            status,
            {"capability": claimed["capability_id"], "decision": result.get("decision"), "error": result.get("error")},
            from_status=work_queue.PROCESSING,
            tenant_id=context.tenant_id,
        )
        if marked is None or marked.get("status") in (work_queue.PENDING, work_queue.PROCESSING):
            return _envelope(EXECUTION_ERROR, error_code="hollow_queue", error_message="process did not change the persisted queue status")
        return _envelope(SUCCESS, output={"item": marked, "result": result}, ok=True)
    if operation == "refuse":
        return _envelope(
            VALIDATION_ERROR,
            error_code="refused",
            error_message=str(args.get("reason") or "refused"),
        )
    return _envelope(EXECUTION_ERROR, error_code="unknown_op", error_message=f"unknown op {operation}")


def authorized_context(tenant_id: str = "local") -> ActionContext:
    return ActionContext(
        tenant_id=tenant_id,
        permissions=[WRITE_PERMISSION, READ_PERMISSION, PROCESS_PERMISSION],
    )


def unauthorized_context(tenant_id: str = "local") -> ActionContext:
    return ActionContext(tenant_id=tenant_id, user_id="stranger", permissions=[])


def _ok_true(result: Mapping[str, Any]) -> bool:
    return result.get("ok") is True or result.get("status") == SUCCESS


async def perform_all(capability_id: Optional[str] = None, tenant_id: str = "local") -> Dict[str, Any]:
    """Walk the ten outcomes against the live store and report each one.

    Coroutine on purpose: the harness performs the ten outcomes with
    ``asyncio.run(perform_all(...))``, and the work itself is store-bound
    (create/read/update/delete plus the queue and refusal cases) rather than
    CPU-bound, so one awaitable entry point is all a caller needs.
    """
    cap = str(capability_id or CAPABILITY_IDS[0])
    entity = entity_of(cap)
    sample = sample_payload(cap)
    context = authorized_context(tenant_id)
    outcomes: Dict[str, Dict[str, Any]] = {}

    def perform(op: str, arguments: Mapping[str, Any], ctx: Optional[ActionContext] = None) -> Dict[str, Any]:
        payload = {**arguments, "capability_id": cap}
        return execute_action(spec_for(op, cap), ctx or context, payload)

    created = perform("create", dict(sample))
    stored = (created.get("output") or {}).get("stored") or {}
    outcomes[OUTCOME_CREATE_PERSISTS] = {
        "status": "performed" if created.get("status") == SUCCESS and stored.get("id") is not None else "failed",
        "id": stored.get("id"),
        "error": created.get("error_message"),
    }
    read = perform("read", {"id": stored.get("id")})
    read_row = (read.get("output") or {}).get("stored") or {}
    outcomes[OUTCOME_READ_RETURNS_PERSISTED] = {
        "status": "performed" if read.get("status") == SUCCESS and read_row.get("id") == stored.get("id") else "failed",
        "id": read_row.get("id"),
    }
    mutated = dict(sample)
    enum = enum_field(cap)
    if enum and len(enum[1]) > 1:
        mutated[enum[0]] = enum[1][1]
    elif "reference" in mutated:
        mutated["reference"] = str(mutated["reference"]) + "-upd"
    update = perform("update", {**mutated, "id": stored.get("id")})
    after = store.get(entity, stored["id"], tenant_id) if stored.get("id") is not None else None
    outcomes[OUTCOME_UPDATE_PERSISTS] = {
        "status": "performed"
        if update.get("status") == SUCCESS and after is not None and all(after.get(k) == mutated[k] for k in mutated)
        else "failed",
        "error": None if after else "update did not persist",
    }
    listed = perform("list", {})
    listed_ids = {(item or {}).get("id") for item in (listed.get("output") or {}).get("items") or []}
    persisted_ids = {row["id"] for row in store.list_all(entity, tenant_id)}
    outcomes[OUTCOME_LIST_ONLY_PERSISTED] = {
        "status": "performed" if listed.get("status") == SUCCESS and listed_ids == persisted_ids and stored.get("id") in listed_ids else "failed",
        "listed": sorted(x for x in listed_ids if x is not None),
        "persisted": sorted(persisted_ids),
    }
    enqueued = perform("enqueue", {"payload": dict(sample)})
    item = (enqueued.get("output") or {}).get("item") or {}
    before = item.get("status")
    processed = perform("process", {"id": item.get("id")}) if item.get("id") else {}
    after_item = work_queue.get(int(item["id"]), tenant_id=tenant_id) if item.get("id") else None
    outcomes[OUTCOME_QUEUE_ITEM_PROCESSED] = {
        "status": "performed"
        if enqueued.get("status") == SUCCESS
        and before == work_queue.PENDING
        and processed.get("status") == SUCCESS
        and after_item is not None
        and after_item.get("status") in (work_queue.PROCESSED, work_queue.FAILED)
        and after_item.get("status") != before
        and after_item.get("result")
        else "failed",
        "before": before,
        "after": (after_item or {}).get("status"),
        "error": None if after_item else "hollow queue",
    }
    refused = perform("refuse", {"reason": "s12-refused"})
    invalid = None
    if enum:
        bad = dict(sample)
        bad[enum[0]] = "__not_in_contract__"
        invalid = perform("create", bad)
    outcomes[OUTCOME_REFUSED_ACTION_ERRORS] = {
        "status": "performed"
        if refused.get("status") != SUCCESS
        and not _ok_true(refused)
        and refused.get("error_message")
        and (invalid is None or (invalid.get("status") != SUCCESS and not _ok_true(invalid)))
        else "failed",
        "refused_status": refused.get("status"),
        "invalid_status": (invalid or {}).get("status"),
    }
    key = f"s12-idempotent-{cap}"
    first = perform("create", {**sample, "idempotency_key": key})
    second = perform("create", {**sample, "idempotency_key": key})
    first_id = ((first.get("output") or {}).get("stored") or {}).get("id")
    second_id = ((second.get("output") or {}).get("stored") or {}).get("id")
    replayed = ((second.get("output") or {}).get("replayed")) is True
    outcomes[OUTCOME_IDEMPOTENT_DUPLICATE_SAFE] = {
        "status": "performed"
        if first.get("status") == SUCCESS and second.get("status") == SUCCESS and first_id is not None and first_id == second_id and replayed
        else "failed",
        "first_id": first_id,
        "second_id": second_id,
        "replayed": replayed,
    }
    denied = execute_action(spec_for("create", cap), unauthorized_context(tenant_id), {**sample, "capability_id": cap})
    outcomes[OUTCOME_UNAUTHORIZED_REJECTED] = {
        "status": "performed"
        if denied.get("status") == PERMISSION_DENIED and not _ok_true(denied) and denied.get("error_code") == "permission_denied"
        else "failed",
        "action_status": denied.get("status"),
        "error_code": denied.get("error_code"),
    }
    required = required_field_names(cap)
    if required:
        incomplete = {k: v for k, v in sample.items() if k != required[0]}
        missing = perform("create", incomplete)
        outcomes[OUTCOME_MISSING_FIELD_REJECTED] = {
            "status": "performed"
            if missing.get("status") == VALIDATION_ERROR and not _ok_true(missing) and missing.get("error_code") == "invalid_input"
            else "failed",
            "field": required[0],
            "action_status": missing.get("status"),
            "error": missing.get("error_message"),
        }
    else:
        outcomes[OUTCOME_MISSING_FIELD_REJECTED] = {"status": "failed", "error": "capability contract declares no required field"}
    doomed = perform("create", dict(sample))
    doomed_id = ((doomed.get("output") or {}).get("stored") or {}).get("id")
    deleted = perform("delete", {"id": doomed_id})
    gone = store.get(entity, doomed_id, tenant_id) if doomed_id is not None else "no-id"
    outcomes[OUTCOME_DELETE_PERSISTS] = {
        "status": "performed" if doomed.get("status") == SUCCESS and deleted.get("status") == SUCCESS and gone is None else "failed",
        "id": doomed_id,
        "remaining": gone,
    }
    failed = [name for name in OUTCOMES if outcomes.get(name, {}).get("status") != "performed"]
    return {
        "ok": not failed,
        "capability_id": cap,
        "entity": entity,
        "outcomes": outcomes,
        "failed": failed,
        "performed": [name for name in OUTCOMES if name not in failed],
        "kernel": "execute_action",
    }
