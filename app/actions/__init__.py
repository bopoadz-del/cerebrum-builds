"""Capability handlers."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['record_checkin', 'todays_arrivals_board', 'room_availability_check', 'guest_notes_and_preferences', 'checkin_notifications', 'daily_checkin_summary', 'audit_trail']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
