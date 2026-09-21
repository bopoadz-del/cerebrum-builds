"""Handler for capability property_and_room_registry.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Maintains the property/room registry: every room is mirrored into the vendored
estate registry (the shared reference the other capabilities read) and its
attributes are analysed by the hotel document engine, so a rate sheet or room
list the desk uploads is interpreted with the same vocabulary.

Scope
-----
READS  the capability's own columns from the caller's record; app.dispatch (the
       local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``property_and_room_registry`` table, through the route's
       tenant-scoped save).
WRITES app.dispatch.execute() results; exactly one row in ``property_and_room_registry`` via the
       ROUTE's tenant-scoped persistence (app.routes) -- this handler has no
       tenant and never persists directly.
NEVER  network egress except through app.notify / an operator-configured URL
       guarded by app.security; ``vendor/**`` (sealed, read-only); another
       capability's table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys (channel, message, steps, table, topic, document
path) are constructed by ``app.block_inputs.prepare_block_input`` from this
record -- the caller is never asked for them.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "property_and_room_registry"
ENTITY = "property_and_room_registry"
BLOCK_IDS = ['estate_registry', 'hotel_v2']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {'estate_registry': 'create', 'hotel_v2': 'analyze'}
#: This capability's own domain columns (the kernel strips trust-scope keys
#: from caller arguments; declaring them here keeps the domain data intact).
CAPABILITY_FIELDS = ['reference', 'status', 'property_name', 'building', 'floor', 'room_number', 'room_type', 'capacity', 'room_status', 'notes']


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)

def _room_identity(data: Dict[str, Any]) -> str:
    """A stable registry id for one room: property, then the room itself."""
    property_name = _text(data, "property_name", 120) or "property"
    room = _text(data, "room_number", 40) or _text(data, "reference", 60) or "room"
    return f"{property_name}:{room}".replace(" ", "_")


def _room_summary(data: Dict[str, Any]) -> str:
    return (
        "Room registry entry. Property: {property}. Building: {building}. "
        "Floor: {floor}. Room: {room}. Type: {kind}. Capacity: {capacity}. "
        "Room status: {room_status}. Notes: {notes}"
    ).format(
        property=_text(data, "property_name", 200) or "unnamed",
        building=_text(data, "building", 120) or "unassigned",
        floor=data.get("floor"),
        room=_text(data, "room_number", 40) or "unassigned",
        kind=_text(data, "room_type", 60) or "standard",
        capacity=data.get("capacity"),
        room_status=_text(data, "room_status", 60) or "available",
        notes=_text(data, "notes", 500),
    )


def _import_store_dir() -> str:
    import os
    from pathlib import Path

    root = Path(os.environ.get("STORAGE_PATH", "./data")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return str(root / "estate_registry")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        room_status = _text(data, "room_status", 60) or "available"
        room_type = _text(data, "room_type", 60) or "standard"
        summary = _room_summary(data)
        registry_id = _room_identity(data)
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    store_dir = _import_store_dir()

    # The registry block is authoritative for existence: list first, then
    # either read the room back (idempotent re-registration) or create it.
    # ``estate_registry`` reads its operation off the record it is handed
    # (``action`` is a declared field of its own input schema), so the
    # operation travels in the payload as well as the keyword; and ``id`` is a
    # required input for every action, so the room's own identity goes with
    # the list call too. Nothing is minted to satisfy a validator.
    listing = runner(
        "estate_registry",
        {"id": registry_id, "store_dir": store_dir},
        action="list",
        payload_extra={"action": "list"},
    )
    records = listing.get("records") if isinstance(listing, dict) else None
    known = {
        str(item.get("id"))
        for item in (records or [])
        if isinstance(item, dict) and item.get("id")
    }

    if registry_id in known:
        registered = runner(
            "estate_registry",
            {"id": registry_id, "store_dir": store_dir},
            action="read",
            payload_extra={"action": "read"},
        )
        registration = "read"
    else:
        registered = runner(
            "estate_registry",
            {
                "id": registry_id,
                "store_dir": store_dir,
                "data": {
                    "property_name": _text(data, "property_name", 200),
                    "building": _text(data, "building", 120),
                    "floor": data.get("floor"),
                    "room_number": _text(data, "room_number", 40),
                    "room_type": room_type,
                    "capacity": data.get("capacity"),
                    "room_status": room_status,
                    "reference": _text(data, "reference", 120),
                },
            },
            action="create",
            payload_extra={"action": "create"},
        )
        registration = "create"

    analysis = runner("hotel_v2", {"text": summary}, action="analyze")
    metrics = analysis.get("metrics") if isinstance(analysis, dict) else {}
    if not isinstance(metrics, dict):
        metrics = {}

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "room": {
            "registry_id": registry_id,
            "registration": registration,
            "room_type": room_type,
            "room_status": room_status,
            "floor": data.get("floor"),
            "capacity": data.get("capacity"),
        },
        "registry_record": registered.get("record") if isinstance(registered, dict) else None,
        "analysis": {
            "document_type": analysis.get("document_type") if isinstance(analysis, dict) else None,
            "metric_count": len([v for v in metrics.values() if isinstance(v, dict) and v.get("value") is not None]),
        },
        "blocks": runner.report(),
    }
