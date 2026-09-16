"""Runtime path resolution for RetailOS.

Written by the factory WRITER role (codewhale exec).

One root for everything the platform writes: ``STORAGE_PATH``. The vendored
Store ``database`` block resolves its own SQLite file from ``DATA_DIR`` and
falls back to ``./data``; left alone that would be a second persistence root
inside the checkout. ``ensure_runtime_paths()`` points ``DATA_DIR`` at
``STORAGE_PATH`` when the operator has not set it, so the platform's records,
its block mirror, its corpus and its audit files all live under one directory
and move together when the volume is mounted.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENSURED = False


def storage_root() -> Path:
    root = Path(os.getenv("STORAGE_PATH") or "./data").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_runtime_paths() -> dict:
    """Idempotent: bind DATA_DIR to STORAGE_PATH unless the operator set it."""
    global _ENSURED
    root = storage_root()
    if not os.getenv("DATA_DIR"):
        os.environ["DATA_DIR"] = str(root)
    if not _ENSURED:
        for name in ("blocks", "corpus", "audit", "documents"):
            (root / name).mkdir(parents=True, exist_ok=True)
        _ENSURED = True
    return {
        "storage_path": str(root),
        "data_dir": os.environ.get("DATA_DIR"),
        "single_root": Path(os.environ.get("DATA_DIR") or root).resolve() == root,
    }
