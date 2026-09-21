"""Handler for capability operations_oversight_dashboard.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Gives management a live, tenant-scoped view of occupancy, room status, open work
orders and guest activity. Every read is authorised first: the vendored RBAC block
evaluates the operator's role against the permission the view needs, and the board
itself is composed by the vendored dashboard block.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``operations_oversight_dashboard`` table, through the route's
       tenant-scoped save); app.formulas (occupancy arithmetic).
WRITES app.dispatch.execute() results; exactly one row in ``operations_oversight_dashboard`` via the
       ROUTE's tenant-scoped persistence (app.routes) -- this handler has no
       tenant and never persists directly.
NEVER  a currency, tax regime or tax rate the brief did not give; unguarded
       network egress; ``vendor/**`` (sealed, read-only); another capability's
       table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "operations_oversight_dashboard"
ENTITY = "operations_oversight_dashboard"
BLOCK_IDS = ['dashboard', 'multi_tenant_rbac']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {'dashboard': 'render', 'multi_tenant_rbac': 'check'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['reference', 'status', 'dashboard_name', 'widget', 'window_days', 'operator_role', 'occupancy_percent', 'open_work_orders', 'notes']


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)

_PERMISSIONS = {
    "admin": ["oversight:read", "oversight:write", "oversight:export"],
    "operator": ["oversight:read"],
}

_WIDGET_KIND = {
    "occupancy": "status_grid",
    "room_status": "status_grid",
    "work_orders": "recent_activity",
    "guest_activity": "recent_activity",
}


def _access(operator_role: str, needed: str) -> Dict[str, Any]:
    return {
        "permissions": list(_PERMISSIONS.get(operator_role, ["oversight:read"])),
        "needed": [needed],
        "mode": "all",
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        dashboard_name = _text(data, "dashboard_name", 120) or "Operations"
        widget = _text(data, "widget", 40) or "occupancy"
        operator_role = _text(data, "operator_role", 20) or "operator"
        window_days = data.get("window_days") or 7
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    access = runner("multi_tenant_rbac", _access(operator_role, "oversight:read"), action="check")
    board = runner(
        "dashboard",
        {
            "status": _text(data, "status", 20) or "open",
            "widget": widget,
            "dashboard_name": dashboard_name,
            "window_days": window_days,
            "occupancy_percent": data.get("occupancy_percent"),
            "open_work_orders": data.get("open_work_orders"),
        },
        action="render",
    )
    snapshot = runner(
        "dashboard",
        {"status": _text(data, "status", 20) or "open", "dashboard_name": dashboard_name},
        action="get_snapshot",
    )

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    metrics = snapshot.get("metrics") if isinstance(snapshot, dict) else {}
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "dashboard": {
            "name": dashboard_name,
            "widget": widget,
            "widget_kind": _WIDGET_KIND.get(widget, "status_grid"),
            "window_days": window_days,
            "occupancy_percent": data.get("occupancy_percent"),
            "open_work_orders": data.get("open_work_orders"),
        },
        "access": {
            "operator_role": operator_role,
            "granted": bool(str(access.get("status", "")).lower() in ("ok", "success")),
            "permissions": _PERMISSIONS.get(operator_role, ["oversight:read"]),
        },
        "rendered": {
            "layout": (board.get("layout") or {}).get("type") if isinstance(board, dict) else None,
            "widgets": len(board.get("widgets") or []) if isinstance(board, dict) else 0,
        },
        "snapshot_metrics": metrics if isinstance(metrics, dict) else {},
        "blocks": runner.report(),
    }
