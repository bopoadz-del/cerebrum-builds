"""Capability handlers for RetailOS.

Written by the factory WRITER role (codewhale exec).

Lazy re-exports only: importing every handler at package import time
would import app.store and the vendored blocks before the routes exist
(the factory forbids eager ``from app.actions import <capability>``
re-exports).
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['analytics_dashboard', 'compliance_and_audit', 'customer_insights', 'inventory_management', 'omnichannel_integration', 'sales_and_orders', 'supplier_and_purchasing']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
