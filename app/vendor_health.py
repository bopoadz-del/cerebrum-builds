"""Live health of the vendored Store blocks this platform binds.

Written by the factory WRITER role (codewhale exec)

Two slices in this checkout cannot load, and a platform that silently bound
them would be lying about its own capabilities:

``notification``
    ``vendor/cerebrum/blocks/notification.py`` does not parse --
    ``IndentationError: expected an indented block after 'try' statement`` at
    line 231 -- so the module cannot be imported, let alone executed.

``knowledge``
    ``vendor/cerebrum/blocks/knowledge.py`` imports
    ``vendor.cerebrum.core.vector_store``, which the vendored core slice does
    not ship, so the RAG knowledge block raises ImportError at import time.

Neither is patched: ``vendor/**`` is sealed and read-only for this seat. Both
are reported here, in ``docs/blockers.json`` and on ``GET /v1/vendor_health``,
and no capability binds them: ``checkin_notifications`` delivers over the
event bus + queue, ``guest_notes_and_preferences`` over database + memory.

Scope
-----
READS  ``vendor/**`` (import probes only, never a write).
WRITES nothing.
NEVER  network, vendor writes, block execution with side effects.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

#: Block id -> why the vendored slice cannot run in this checkout.
KNOWN_DEFECTS: Dict[str, str] = {'notification': "vendor/cerebrum/blocks/notification.py does not parse: IndentationError: expected an indented block after 'try' statement on line 230 (notification.py, line 231) -- the Store notify slice cannot be imported at all, so notification/event_bus MCP push cannot run. Mitigation: checkin_notifications delivers the alert over the event_bus publish path with a durable queue follow-up.", 'knowledge': "vendor/cerebrum/blocks/knowledge.py imports vendor.cerebrum.core.vector_store, which the vendored core slice does not ship (ImportError: cannot import name 'vector_store' from 'vendor.cerebrum.core'). The knowledge block cannot load. Mitigation: guest_notes_and_preferences stores notes through the database block and caches them in the memory block; tenant retrieval runs through app/retrieval.py."}


def probe_block(block_id: str) -> Dict[str, Any]:
    """Can this block actually run? Adapter first, then the Store class."""
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
        "degraded_capabilities": {},
        "note": (
            "unavailable blocks are named, never stubbed: see docs/blockers.json "
            "for the fallback each capability uses instead"
        ),
    }
