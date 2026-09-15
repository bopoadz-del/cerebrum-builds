"""Revision identity for fail-closed health and rollback drills."""

from __future__ import annotations

import os

MARK_BASELINE = "baseline"
MARK_CHANGED = "changed"
REVISION_N = "1.0.0"
REVISION_N_PLUS_1 = "1.0.1"


def current_app_revision() -> str:
    return os.environ.get("APP_REVISION") or REVISION_N


def current_app_mark() -> str:
    return os.environ.get("APP_MARK") or MARK_BASELINE
