"""Capability handlers.

PEP 562 lazy access: ``from app.actions import <capability>`` works, but the
package never eagerly imports its siblings. An eager re-export plus a handler
that imports app.routes at load time is the circular-import class that makes a
generated workspace fail to import before any route is honest.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['call_state_machine', 'crm_destination_placeholder', 'google_drive', 'lead_intake_and_dial_queue', 'local_drive', 'mcp_adapter', 'notification', 'outcome_capture_and_ledger', 'project_knowledge_grounding', 'qualification_and_broker_summary', 'voice_gateway', 'warm_transfer']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
