"""Capability handlers."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['patient_records', 'appointment_scheduling', 'treatment_management', 'billing_invoicing', 'inventory_management', 'audit_trail', 'role_management', 'clinic_analytics']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
