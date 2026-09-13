"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _sku(payload: Dict[str, Any]) -> str:
    return str(payload.get("sku") or _ref(payload))


def _product(payload: Dict[str, Any]) -> str:
    return str(payload.get("product_name") or payload.get("shop_name") or "sample")


def _qty(payload: Dict[str, Any], key: str = "quantity") -> int:
    raw = payload.get(key)
    if raw in (None, "", "sample"):
        return 0 if key == "threshold" else 1
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0 if key == "threshold" else 1


def _summary(payload: Dict[str, Any]) -> str:
    return (
        f"retail inventory {_ref(payload)} sku={_sku(payload)} "
        f"product={_product(payload)} status={payload.get('status', 'open')}"
    )


def attach_result(block_input: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Store kit shims read input['result']; schema-sample POSTs omit that key."""
    if "result" not in block_input:
        block_input["result"] = {
            "reference": _ref(payload),
            "status": payload.get("status", "open"),
            "sku": _sku(payload),
        }
    return block_input


def database_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return attach_result(
        {
            "table": "inventory_stock_tracking",
            "filters": {"reference": _ref(payload)},
        },
        payload,
    )


def storage_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return attach_result(
        {
            "filename": f"{_sku(payload)}.json",
            "content": {
                "reference": _ref(payload),
                "sku": _sku(payload),
                "product_name": _product(payload),
                "status": payload.get("status", "open"),
            },
            "metadata": {"capability": payload.get("capability") or "inventory_stock_tracking"},
        },
        payload,
    )


def validation_input(payload: Dict[str, Any], item_type: str = "inventory_sku") -> Dict[str, Any]:
    quantity = _qty(payload, "quantity") if "quantity" in payload or item_type == "inventory_sku" else _qty(
        payload, "adjustment_qty"
    )
    item = {
        "id": _ref(payload),
        "type": item_type,
        "sku": _sku(payload),
        "quantity": quantity,
        "status": payload.get("status", "open"),
    }
    return attach_result(
        {
            "item": item,
            "context": {
                "capability": payload.get("capability") or item_type,
                "shop": payload.get("shop_name") or payload.get("location") or "tiny-smoke",
            },
        },
        payload,
    )


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "unattributed")
    return attach_result(
        {
            "category": payload.get("category") or "admin",
            "user_id": actor,
            "event_action": payload.get("event_action") or "persist",
            "resource": _ref(payload),
            "details": {
                "status": payload.get("status", "open"),
                "summary": _summary(payload),
                "sku": _sku(payload),
                "actor": actor,
                "actor_role": payload.get("actor_role"),
                "capability": payload.get("capability"),
            },
        },
        payload,
    )


def event_bus_input(payload: Dict[str, Any], topic: str | None = None) -> Dict[str, Any]:
    """Prepared event_bus publish envelope. Never forward the raw schema sample."""
    message = _summary(payload)
    chosen = topic or str(
        payload.get("event")
        or payload.get("event_type")
        or payload.get("event_name")
        or payload.get("reminder_type")
        or f"inventory.{_sku(payload)}"
    )
    return attach_result(
        {
            "topic": chosen,
            "payload": {
                "reference": _ref(payload),
                "sku": _sku(payload),
                "status": payload.get("status", "open"),
            },
            "message": message,
            "channel": "mcp",
            "tool": "event_bus",
        },
        payload,
    )


def notification_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = f"low stock {_sku(payload)} threshold={_qty(payload, 'threshold')} {_product(payload)}"
    return attach_result(
        {
            "channel": "mcp",
            "tool": "event_bus",
            "block": "event_bus",
            "message": message,
            "topic": f"inventory.low_stock.{_sku(payload)}",
            "payload": {
                "reference": _ref(payload),
                "sku": _sku(payload),
                "threshold": _qty(payload, "threshold"),
            },
            "params": {"action": "publish"},
        },
        payload,
    )


def queue_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return attach_result(
        {
            "job_type": "low_stock_alert",
            "queue": "inventory-alerts",
            "payload": {
                "reference": _ref(payload),
                "sku": _sku(payload),
                "threshold": _qty(payload, "threshold"),
            },
            "priority": 1,
        },
        payload,
    )


def team_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "operator")
    name = str(payload.get("shop_name") or payload.get("member_name") or f"shop-{_ref(payload)}")
    return attach_result(
        {
            "user_id": actor,
            "name": name,
            "slug": f"tiny-smoke-{_ref(payload)}".lower().replace(" ", "-"),
            "plan": "free",
        },
        payload,
    )


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return attach_result(
        {
            "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
            "title": f"Tiny Smoke inventory {_ref(payload)}",
            "theme": "light",
            "layout": "grid",
            "summary": _summary(payload),
            "horizon": payload.get("horizon") or "daily",
            "shop_name": payload.get("shop_name") or "tiny-smoke",
        },
        payload,
    )


def analytics_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return attach_result(
        {
            "metric": "inventory_on_hand",
            "value": _qty(payload, "quantity") if "quantity" in payload else 1,
            "tags": {
                "sku": _sku(payload),
                "shop": str(payload.get("shop_name") or "tiny-smoke"),
                "horizon": str(payload.get("horizon") or "daily"),
                "reference": _ref(payload),
            },
        },
        payload,
    )


def prepared_event_bus_step(payload: Dict[str, Any], topic: str | None = None) -> Dict[str, Any]:
    """Exact factory-grounded event_bus workflow child (step_0 / step_1 / step_2+)."""
    body = event_bus_input(payload, topic=topic)
    return {
        "block": "event_bus",
        "action": "publish",
        "params": {"action": "publish"},
        "input": body,
    }


def workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Stock adjustment pipeline. result is attached so kit shims do not KeyError."""
    first = attach_result(validation_input(payload, item_type="stock_adjustment"), payload)
    audit_body = audit_input({**payload, "event_action": "stock_adjust", "category": "admin"})
    steps: List[Dict[str, Any]] = [
        {
            "id": "step_0",
            "block": "validation",
            "action": "validate_pipeline",
            "params": {"action": "validate_pipeline"},
            "input": first,
        },
        {
            "id": "step_1",
            "block": "audit",
            "action": "log",
            "params": {"action": "log"},
            "input": audit_body,
        },
    ]
    return attach_result(
        {
            "pipeline_id": f"stock-adjust-{_ref(payload)}",
            "steps": steps,
        },
        payload,
    )


def record_mutation_audit(
    principal: Any,
    *,
    action: str,
    resource: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Emit a Principal-attributed audit event for a mutation (no phantom entity)."""
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute

    extra = dict(details or {})
    payload = {
        "reference": resource,
        "status": extra.pop("status", "open"),
        "actor": principal.subject,
        "actor_role": principal.role,
        "event_action": action,
        "category": extra.pop("category", "admin"),
        **extra,
    }
    execute("audit", audit_input(payload), action=BLOCK_DEFAULT_ACTIONS.get("audit"))
    return payload
