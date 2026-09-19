"""Capability handlers for the Bakery Chain Operations & Delivery Platform.

One module per capability, each exporting ``CAPABILITY_ID`` and
``handle(payload)``. Nothing is re-exported eagerly here: importing
``app.actions`` must not import a capability module (a capability module
imports ``app.dispatch``, and an eager re-export is the circular import that
stops the workspace from importing at all).
"""

from __future__ import annotations

__all__ = (
    "CAPABILITY_IDS",
    "handler_for",
)

CAPABILITY_IDS = (
    "stock_inventory_management",
    "delivery_dispatch_tracking",
    "document_knowledge_qa",
    "fleet_cost_and_pricing",
    "management_reporting_dashboard",
    "user_roles_workforce",
    "operational_procedures_readiness",
    "audit_evidence_trail",
)


def handler_for(capability_id: str):
    """Import and return ``handle`` for *capability_id* (lazy, no re-export)."""
    import importlib

    name = str(capability_id or "").replace("-", "_")
    module = importlib.import_module(f"app.actions.{name}")
    return module.handle
