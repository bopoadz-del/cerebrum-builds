"""Capability handlers."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['patient_and_owner_records', 'appointment_scheduling', 'clinical_visit_notes_and_treatment_plans', 'vaccination_tracking', 'billing_and_invoicing', 'analytics_and_reporting', 'compliance_and_audit_trail', 'client_communication_and_reminders']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
