"""Deploy revision identity for the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

A deploy answers ``/health`` with the revision and mark it was *performed* at,
not the one it hopes for. Both are read from the process environment at request
time (``APP_REVISION`` / ``APP_MARK``), so a rollback that changes the
environment changes the answer on the next request without a restart — and a
rollback that forgets to change it is visible as a stale identity rather than a
silent lie.

``REVISION_N``/``MARK_BASELINE`` describe the shipping build;
``REVISION_N_PLUS_1``/``MARK_CHANGED`` are the next deploy the rollback drill
moves to and back from.

Scope
-----
READS  ``APP_REVISION``, ``APP_MARK``, ``bakery_revision`` file (optional).
WRITES nothing.
NEVER  network, ``vendor/**``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

#: The revision this tree ships as, and the mark that identifies it.
REVISION_N = "bakery-1.0.0"
MARK_BASELINE = "baseline"

#: The next revision a deploy moves to (rollback drill).
REVISION_N_PLUS_1 = "bakery-1.0.1"
MARK_CHANGED = "changed"

ENV_REVISION = "APP_REVISION"
ENV_MARK = "APP_MARK"


def _stamped_revision() -> str:
    """A build may drop its revision next to the package; env always wins."""
    path = Path(__file__).resolve().parents[1] / "bakery_revision"
    if path.is_file():
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
        if value:
            return value
    return ""


def active_revision() -> str:
    """The revision this process is running as."""
    return (os.environ.get(ENV_REVISION) or "").strip() or _stamped_revision() or REVISION_N


def active_mark() -> str:
    """The mark (baseline / changed / …) this process is running as."""
    return (os.environ.get(ENV_MARK) or "").strip() or MARK_BASELINE


def identity() -> Tuple[str, str]:
    """``(revision, mark)`` as the health surface reports them."""
    return active_revision(), active_mark()
