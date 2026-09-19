"""Capability handlers."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['patient_visit_records', 'appointment_scheduling', 'todays_appointment_list', 'day_before_email_reminders', 'patient_directory', 'clinical_history_search', 'role_based_access']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
