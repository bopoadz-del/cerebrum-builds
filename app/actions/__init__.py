"""Capability handlers.

PEP 562 lazy access: ``from app.actions import <capability>`` works, but the
package never eagerly imports its siblings. An eager re-export plus a handler
that imports app.routes at load time is the circular-import class that makes a
generated workspace fail to import before any route is honest.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['document_and_knowledge_answers', 'external_integration_adapter', 'front_desk_and_guest_stay', 'guest_engagement_and_segmentation', 'housekeeping_and_maintenance', 'operations_billing', 'operations_oversight_dashboard', 'property_and_room_registry']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
