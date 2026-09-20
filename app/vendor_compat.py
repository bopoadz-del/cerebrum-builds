"""Import-time compatibility for the vendored Store blocks.

Written by the factory WRITER role (codewhale exec)

Two facts about the sealed vendor tree in this checkout, both verified by
importing it:

1. ``vendor/cerebrum/blocks/document_engine/__init__.py`` loads its wrapper
   with ``spec_from_file_location(..., ".." / "document_engine_block.py")``
   and raises ``FileNotFoundError`` because the CLONER vendored that wrapper
   as the package ``vendor/cerebrum/blocks/document_engine_block/`` (a
   directory) instead of a module file. The package itself imports cleanly
   and exposes the real ``DocumentEngineBlock``. Registering it under the
   name the loader expects is what the loader's own
   ``if _BLOCK_MODULE_NAME in sys.modules`` branch is for.

2. ``vendor/cerebrum/blocks/knowledge.py`` imports ``vector_store`` from
   ``vendor.cerebrum.core``, and that module is not vendored at all.
   ``app.retrieval`` supplies the two async hooks the block calls
   (``search_vectors`` / ``upsert_vectors``) so the block searches this
   platform's own tenant-scoped index.

``notification`` is deliberately NOT shimmed. Its vendored source does not
parse (a bare ``try:`` at line 230), so there is no block to run; the
handlers report it as unavailable by name and ``app.notifications`` does
the delivery. The distinction is the point: a packaging mismatch is
repaired, a broken block is disclosed.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any, Dict, Optional

_INSTALLED = False
NOTES: Dict[str, str] = {}


def _install_document_engine() -> None:
    name = "vendor.cerebrum.blocks.document_engine_block"
    if name in sys.modules:
        return
    module = importlib.import_module(name)
    sys.modules.setdefault(name, module)
    NOTES["document_engine"] = (
        "wrapper package registered under the module name its own loader expects"
    )


def _install_vector_store() -> None:
    name = "vendor.cerebrum.core.vector_store"
    if name in sys.modules:
        return
    try:
        importlib.import_module(name)
        return
    except ImportError:
        pass
    try:
        from app import retrieval
    except ImportError:
        return
    import types

    module = types.ModuleType(name)
    module.search_vectors = retrieval.search_vectors
    module.upsert_vectors = retrieval.upsert_vectors
    module.embed_text = retrieval.embed_text
    module.__all__ = ["search_vectors", "upsert_vectors", "embed_text"]
    sys.modules[name] = module
    NOTES["knowledge"] = "tenant-scoped retrieval index supplied for vector_store"


def install() -> Dict[str, str]:
    """Idempotent. Called by app.dispatch before the first block load."""
    global _INSTALLED
    if _INSTALLED:
        return dict(NOTES)
    for installer in (_install_document_engine, _install_vector_store):
        try:
            installer()
        except Exception as exc:  # noqa: BLE001 - a failed repair must be visible, not fatal
            NOTES[installer.__name__] = f"not applied: {type(exc).__name__}: {exc}"
    _INSTALLED = True
    return dict(NOTES)


_UNAVAILABLE_CACHE: Dict[str, Optional[str]] = {}


def _store_module_failure(block_id: str) -> Optional[str]:
    """Does the Store class this adapter wraps import at all?

    The adapter module can import cleanly (it only imports get_block) while
    the Store class it resolves at call time does not -- the notification
    adapter is exactly that: its own source is fine, and
    ``vendor/cerebrum/blocks/notification.py`` does not parse. A block with
    no Store module at all (``capture``) is self-contained and is available.
    """
    name = f"vendor.cerebrum.blocks.{block_id}"
    try:
        importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if name in str(exc):
            return None
        return f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001 - a broken vendored module is the finding
        return f"{type(exc).__name__}: {exc}"
    return None


def unavailable_reason(block_id: str) -> Optional[str]:
    """The named reason a block cannot load, or None when it loads.

    Cached: a vendored module that fails to import fails the same way every
    time, and re-executing a broken import per call would spam stderr.
    """
    key = str(block_id or "")
    if key in _UNAVAILABLE_CACHE:
        return _UNAVAILABLE_CACHE[key]
    from app.dispatch import load_block

    reason: Optional[str] = None
    try:
        load_block(key)
    except Exception as exc:  # noqa: BLE001 - report, never raise
        reason = f"{type(exc).__name__}: {exc}"
    if reason is None:
        reason = _store_module_failure(key)
    _UNAVAILABLE_CACHE[key] = reason
    return reason
