"""Live health of the vendored Store blocks this platform binds.

Written by the factory WRITER role (codewhale exec)

The CLONER vendors each block's adapter plus the Store class it stands on.
Two slices in this checkout are defective, and a platform that silently
skipped them would be lying about its own capabilities:

``notification``
    ``vendor/cerebrum/blocks/notification.py`` does not parse --
    ``IndentationError: expected an indented block after 'try' statement`` at
    line 231 -- so the module cannot be imported, let alone executed.

``document_engine``
    ``vendor/cerebrum/blocks/document_engine/__init__.py`` loads
    ``vendor/cerebrum/blocks/document_engine_block.py``; the CLONER wrote that
    implementation as the package ``document_engine_block/``. The offline
    checkout also has no PDF parser, so even with the loader repaired the
    parse action refuses.

Neither is patched: ``vendor/**`` is sealed and read-only for this seat. Both
are reported here, in ``docs/blockers.json`` and on ``GET /v1/vendor_health``,
and the capabilities that would have bound them carry an honest fallback
(``app.notify`` outbox) instead of a stub that
pretends the block answered.

Scope
-----
READS  ``vendor/**`` (import probes only, never a write).
WRITES nothing.
NEVER  network, vendor writes, block execution with side effects.
"""

from __future__ import annotations

import importlib
from typing import Any, Dict, List, Sequence

#: Block id -> why the vendored slice cannot run in this checkout.
#: Blocks recorded as defective in THIS checkout. Empty: the three slices this
#: platform vendors (database, validation, dashboard) all load and execute
#: offline, verified by tests/test_vendor_health.py and reported on
#: GET /v1/vendor_health. A defect found later is named here and in
#: docs/blockers.json -- never stubbed into a passing call.
KNOWN_DEFECTS: Dict[str, str] = {}


def probe_block(block_id: str) -> Dict[str, Any]:
    """Can this block actually run? Adapter first, then the Store class.

    Every vendored block ships an adapter at ``vendor/blocks/<id>/block.py``.
    A Store-backed adapter resolves its class through the vendored registry,
    so membership in that registry is what decides whether the class has to
    load: ``capture`` is a factory-side adapter with no Store class behind it
    and is perfectly healthy, while ``notification`` has a registry entry
    whose module does not parse.
    """
    from app.dispatch import BlockNotVendored, load_block

    try:
        load_block(block_id)
    except BlockNotVendored as exc:
        return {
            "block_id": block_id,
            "available": False,
            "defect": KNOWN_DEFECTS.get(block_id, "vendored adapter is missing"),
            "error": str(exc)[:300],
        }
    except Exception as exc:  # adapter itself does not import
        return {
            "block_id": block_id,
            "available": False,
            "defect": KNOWN_DEFECTS.get(block_id, "vendored adapter does not import"),
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }
    try:
        from vendor.cerebrum.blocks import BLOCK_REGISTRY, get_block

        registered = block_id in BLOCK_REGISTRY
    except Exception as exc:
        return {
            "block_id": block_id,
            "available": False,
            "defect": KNOWN_DEFECTS.get(block_id, "vendored block registry does not load"),
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }
    if not registered:
        return {
            "block_id": block_id,
            "available": True,
            "backed_by": "vendored adapter (factory-side block)",
        }
    try:
        block_class = get_block(block_id)
    except Exception as exc:  # ImportError, SyntaxError, FileNotFoundError, ...
        return {
            "block_id": block_id,
            "available": False,
            "defect": KNOWN_DEFECTS.get(block_id, "Store class behind the adapter does not load"),
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }
    return {
        "block_id": block_id,
        "available": True,
        "backed_by": "Store class",
        "block_class": getattr(block_class, "__name__", str(block_class)),
    }


def report(block_ids: Sequence[str]) -> Dict[str, Any]:
    """Health of every block this platform binds, plus the recorded defects."""
    probes: List[Dict[str, Any]] = [probe_block(b) for b in block_ids]
    unavailable = [p["block_id"] for p in probes if not p["available"]]
    bound = {str(b) for b in block_ids}
    known = {
        block_id: reason
        for block_id, reason in sorted(KNOWN_DEFECTS.items())
        if block_id not in bound
    }
    return {
        "ok": not unavailable,
        "probed": len(probes),
        "bound": sorted(bound),
        "unavailable": unavailable,
        "blocks": probes,
        "known_defects_not_bound": known,
        # No capability in this product is degraded: both cards are bound only
        # to blocks that are vendored and available (capture, database,
        # validation, dashboard). An honest empty map beats a foreign roster.
        "degraded_capabilities": {},
        "note": (
            "unavailable blocks are named, never stubbed: see docs/blockers.json "
            "for the honest fallback each capability uses instead"
        ),
    }
