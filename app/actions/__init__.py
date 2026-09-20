"""Capability handlers."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['job_and_site_tracking', 'commercials_and_valuations', 'document_qa_and_indexing', 'safety_and_compliance', 'progress_cost_dashboard', 'automation_reminders_escalation', 'audit_and_access_control', 'team_notifications']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
