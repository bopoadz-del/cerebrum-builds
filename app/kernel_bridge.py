"""Bridge a sync ``handle(payload)`` through the action runner.

The HTTP route calls ``handle`` directly; this bridge adapts the same
handler to the product kernel's ActionSpec shape, so a kernel-driven caller
(MCP, the queue processor, a test harness) runs exactly the code the route
runs. Persistence stays in the route/envelope, never in the handler.

The vendored kernel is used when it is present; otherwise the compatible
shim in ``app/domain_ops.py`` is, so this module works in both trees.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.actions import handle_for
from app.domain_ops import ActionContext, ActionSpec, execute_action
from app.models import MODELS


def _run_handler(capability_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return handle_for(capability_id).handle(dict(payload or {}))


def spec_for(capability_id: str) -> ActionSpec:
    """The ActionSpec for one capability, wired to its own handler."""
    capability_id = str(capability_id)
    if capability_id not in MODELS:
        raise KeyError(f"unknown capability: {capability_id}")
    from app.domain_ops import READ_PERMISSION, WRITE_PERMISSION

    return ActionSpec(
        action_id=f"product.{capability_id}",
        name="invoke",
        permissions=[WRITE_PERMISSION, READ_PERMISSION],
        description=MODELS[capability_id].DESCRIPTION,
    )


def invoke(capability_id: str, payload: Dict[str, Any], *, tenant_id: str) -> Dict[str, Any]:
    """Run a capability handler under a caller's trust scope."""
    outcome = _run_handler(capability_id, payload)
    return {
        "ok": outcome.get("ok") is not False,
        "capability": capability_id,
        "tenant_id": tenant_id,
        "outcome": outcome,
    }


def kernel_available() -> bool:
    """Whether the vendored product kernel is importable in this tree."""
    try:
        import app.cerebrum_product_kernel  # noqa: F401
    except Exception:
        return False
    return True
