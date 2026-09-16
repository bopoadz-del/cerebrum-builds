"""Capability handlers."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['list_todays_check_ins', 'record_check_in']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
