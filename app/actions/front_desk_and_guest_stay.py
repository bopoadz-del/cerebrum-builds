"""Handler for capability front_desk_and_guest_stay.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Runs the guest stay lifecycle operationally: the arrival is analysed by the
hotel document engine (reservation vocabulary, rate codes, risk flags) and a
stay pipeline records the check-in card in the estate registry, so front desk,
housekeeping and billing all read one stay record.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``front_desk_and_guest_stay`` table, through the route's
       tenant-scoped save).
WRITES app.dispatch.execute() results; exactly one row in ``front_desk_and_guest_stay`` via the
       ROUTE's tenant-scoped persistence (app.routes) -- this handler has no
       tenant and never persists directly.
NEVER  unguarded network egress; ``vendor/**`` (sealed, read-only); another
       capability's table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record -- the caller is
never asked for them. Every workflow child step is constructed here, fully
specified, so no child reaches the pipeline unprepared.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "front_desk_and_guest_stay"
ENTITY = "front_desk_and_guest_stay"
BLOCK_IDS = ['hotel_v2', 'workflow']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {'hotel_v2': 'analyze', 'workflow': 'run'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['reference', 'status', 'guest_name', 'room_number', 'arrival_date', 'departure_date', 'guests_count', 'stay_status', 'folio_currency', 'notes']


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)

def _registry_dir() -> str:
    import os
    from pathlib import Path

    root = Path(os.environ.get("STORAGE_PATH", "./data")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return str(root / "estate_registry")


def _stay_summary(data: Dict[str, Any]) -> str:
    return (
        "Reservation and guest stay record. Guest: {guest}. Room: {room}. "
        "Arrival: {arrival}. Departure: {departure}. Guests: {count}. "
        "Stay status: {stay_status}. Folio currency: {currency}. Notes: {notes}"
    ).format(
        guest=_text(data, "guest_name", 200) or "unnamed guest",
        room=_text(data, "room_number", 40) or "unassigned",
        arrival=_text(data, "arrival_date", 40),
        departure=_text(data, "departure_date", 40),
        count=data.get("guests_count"),
        stay_status=_text(data, "stay_status", 60) or "reserved",
        currency=_text(data, "folio_currency", 12) or "unset",
        notes=_text(data, "notes", 500),
    )


def _step(step_id: str, block: str, block_input: Dict[str, Any]) -> Dict[str, Any]:
    """One fully specified workflow child.

    ``prepare_block_input`` shapes each child's input and attaches the
    ``result`` key the workflow shim reads; nothing is left to the caller.
    """
    return {
        "id": step_id,
        "block": block,
        "action": BLOCK_DEFAULT_ACTIONS.get(block),
        "input": block_input,
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        guest = _text(data, "guest_name", 200)
        room = _text(data, "room_number", 40)
        stay_status = _text(data, "stay_status", 60) or "reserved"
        summary = _stay_summary(data)
        reference = _text(data, "reference", 120) or "stay"
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    arrival_analysis = runner("hotel_v2", {"text": summary}, action="analyze")

    # The registry block owns existence and it refuses a duplicate id: a
    # repeated submission of the same stay is the same stay, not a new one.
    # The handler lists first, then either registers the card in the pipeline
    # or reads back the card already on file. The branch belongs here because
    # a workflow step always runs its child with the child's own default
    # action (``create``) -- a step cannot be asked to read instead.
    registry_id = f"stay:{reference}".replace(" ", "_")
    store_dir = _registry_dir()
    probe = block_runner(
        entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS
    )
    listing = probe(
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

    steps = [_step("step_0", "hotel_v2", {"text": summary})]
    on_file: Any = None
    if registry_id in known:
        # Already registered: read the card rather than mint a duplicate.
        registration = "read"
        on_file = runner(
            "estate_registry",
            {"id": registry_id, "store_dir": store_dir},
            action="read",
            payload_extra={"action": "read"},
        )
    else:
        registration = "create"

    stay_card = {
        "reference": reference,
        "guest_name": guest,
        "room_number": room,
        "arrival_date": _text(data, "arrival_date", 40),
        "departure_date": _text(data, "departure_date", 40),
        "guests_count": data.get("guests_count"),
        "stay_status": stay_status,
    }
    if registration == "create":
        # Registered by the pipeline: the child runs ``estate_registry``'s own
        # default action (``create``), with the card constructed here.
        steps.append(
            _step(
                "step_1",
                "estate_registry",
                {
                    "id": registry_id,
                    "data": stay_card,
                    "store_dir": store_dir,
                },
            )
        )

    pipeline = runner(
        "workflow",
        {
            "pipeline_id": f"guest-stay-{reference}".replace(" ", "_"),
            "timeout": 30,
            "result": {"reference": reference, "guest_name": guest, "room_number": room},
            "steps": steps,
        },
        action="run",
    )

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    steps = pipeline.get("results") if isinstance(pipeline, dict) else []
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "stay": {
            "guest_name": guest,
            "room_number": room,
            "stay_status": stay_status,
            "arrival_date": _text(data, "arrival_date", 40),
            "departure_date": _text(data, "departure_date", 40),
            "registry_id": registry_id,
            "registration": registration,
            "registry_record": on_file,
        },
        "front_desk_analysis": {
            "document_type": arrival_analysis.get("document_type")
            if isinstance(arrival_analysis, dict) else None,
        },
        "workflow": {
            "status": pipeline.get("status") if isinstance(pipeline, dict) else None,
            "steps": [
                {"step_id": item.get("step_id"), "block": item.get("block"),
                 "status": item.get("status")}
                for item in (steps or [])
                if isinstance(item, dict)
            ],
        },
        "blocks": runner.report(),
    }
