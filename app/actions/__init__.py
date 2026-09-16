"""Capability handlers for LexManage.

Written by the factory WRITER role (codewhale exec).

Lazy re-exports only: importing every handler at package import time
would import app.store and the vendored blocks before the routes exist
(the factory forbids eager ``from app.actions import <capability>``
re-exports).
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['matter_management', 'client_intake', 'document_management', 'time_and_billing', 'client_portal', 'legal_analytics', 'compliance_audit']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
