"""Capability handlers."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['complaints_management', 'auto_assignment', 'workforce_management', 'management_dashboards', 'reporting', 'role_based_access', 'erp_integration', 'booking_system_integration']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
