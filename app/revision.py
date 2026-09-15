"""Deploy identity. Health reports these; rollback changes the mark, not the rows."""

from __future__ import annotations

import os

MARK_BASELINE = "baseline"
MARK_CHANGED = "changed"
REVISION_N = "rev-n"
REVISION_N_PLUS_1 = "rev-n-plus-1"


def current_revision() -> str:
    return os.environ.get("APP_REVISION") or REVISION_N


def current_mark() -> str:
    return os.environ.get("APP_MARK") or MARK_BASELINE
