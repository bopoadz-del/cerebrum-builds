"""Capability handlers.

Lazy re-exports only: attribute access resolves the capability module on
first use. Eagerly re-exporting every handler here would make app.dispatch
import this package, which imports app.dispatch -- the circular import that
leaves a generated workspace unable to import at all.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ['budget_planning_tracking', 'spend_capture_categorisation', 'approval_workflow', 'variance_analytics', 'dashboard_portfolio_rollup', 'audit_evidence_validation', 'finance_document_knowledge', 'integrations_placeholders']


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
