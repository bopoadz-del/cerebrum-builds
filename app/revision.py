"""Deploy identity. Rollback keeps rows; only the mark/revision label changes."""

from __future__ import annotations

import os

REVISION_N = "0001_baseline"
REVISION_N_PLUS_1 = "0002_lifecycle_audit"
MARK_BASELINE = "baseline"
MARK_CHANGED = "changed"


def current_revision_label() -> str:
    return os.environ.get("APP_REVISION") or REVISION_N


def current_mark() -> str:
    return os.environ.get("APP_MARK") or MARK_BASELINE
