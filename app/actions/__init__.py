"""Capability handlers."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['branch_and_consolidated_operations', 'inventory_and_replenishment', 'branch_books_and_accounting', 'delivery_and_dispatch', 'order_follow_up', 'events_supply', 'document_grounded_knowledge', 'outlook_branch_messaging_integration']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
