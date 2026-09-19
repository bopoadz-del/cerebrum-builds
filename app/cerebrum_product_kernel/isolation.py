"""Isolation guards: the platform runs offline, in one process, on one file.

Every guard here raises instead of warning: a generated platform that quietly
reaches the network or opens a second database is not the product that was
certified.
"""

from __future__ import annotations

import os
from pathlib import Path

from app import store


class IsolationError(RuntimeError):
    """The platform left its declared isolation boundary."""


def assert_single_persistence_root() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data")).resolve()
    files = sorted(path.name for path in root.rglob("*.db")) if root.is_dir() else []
    if len(files) > 1:
        raise IsolationError(
            "more than one database under STORAGE_PATH: " + ", ".join(files)
        )
    return root


def assert_offline() -> None:
    """No provider credential is read and no egress host is configured."""
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
                 "DEEPSEEK_API_KEY", "STORE_URL", "CEREBRUM_STORE_URL"):
        if os.environ.get(name):
            raise IsolationError(f"{name} is set; this platform ships offline")


def assert_entity_migrated(entity: str) -> None:
    conn = store.connect()
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (entity,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise IsolationError(f"entity {entity!r} has no migrated table")
