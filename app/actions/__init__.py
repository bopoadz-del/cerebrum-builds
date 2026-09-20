"""Capability handlers."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['fleet_registry', 'rental_contract_management', 'maintenance_scheduling', 'pricing_and_rate_cards', 'invoicing_and_deposits', 'multi_branch_rollup', 'reporting_analytics', 'audit_trail']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
