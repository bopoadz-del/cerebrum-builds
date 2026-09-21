"""Handler for capability crm_destination_placeholder.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

MARKED PLACEHOLDER, NOT A WORKING INTEGRATION. The destination for a call
outcome plus broker summary -- Salesforce, HubSpot, Zoho, or something the
brokerage has not named -- was never stated in the brief. So this capability
records the intent and the shape of the eventual push and claims nothing
more: the vendored ``mock_connector_bus`` block is asked which systems have a
live integration (answer: none -- every entry is ``mock_unavailable`` and no
operational data is fabricated), and the vendored ``webhook`` block registers
the destination the operator would give, offline, without sending anything.

The moment a CRM destination is named, the recorded shape below is the
payload contract; until then ``delivery_state`` stays ``stubbed`` and the
record says so in its own columns.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``crm_destination_placeholder`` table,
       through the route's tenant-scoped save).
WRITES app.dispatch.execute() results; a registered webhook destination
       (in-process registry only -- nothing is sent); exactly one row in
       ``crm_destination_placeholder`` via the ROUTE's ``store.save(entity,
       record, tenant_id)`` -- this handler has no tenant and never persists
       directly.
NEVER  claiming a working CRM integration; sending a record to an unstated
       destination; unguarded network egress; ``vendor/**`` (sealed,
       read-only); another capability's table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "crm_destination_placeholder"
ENTITY = "crm_destination_placeholder"
BLOCK_IDS = ['mock_connector_bus', 'webhook']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {'mock_connector_bus': 'systems', 'webhook': 'register'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'crm_system', 'destination_url', 'payload_shape',
    'delivery_state', 'mock_mode', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'crm_system': {'allowed_values': ['unstated', 'salesforce', 'hubspot', 'zoho'],
                   'required': True},
    'delivery_state': {'allowed_values': ['queued', 'stubbed', 'refused'],
                       'required': False},
}

#: The connector systems the vendored mock bus carries. A CRM is not among
#: them: that absence is the placeholder this capability reports.
_BUS_SYSTEMS = ("opera", "micros", "grms", "gaming_cms", "loyalty_lms", "maximo")

#: The shape the eventual push will carry. Recorded, not sent.
PAYLOAD_SHAPE = {
    "call_sid": "string",
    "outcome": "project_interested | other_re_interested | not_interested",
    "collected": {
        "property_type": "string",
        "budget": "number",
        "area": "string",
        "timeline": "string",
    },
    "broker_summary": "string",
    "citation": "string",
}


def _text(data: Dict[str, Any], name: str, limit: int = 4000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "crm-destination"
        system = _text(data, "crm_system", 40).lower() or "unstated"
        destination_url = _text(data, "destination_url", 500)
        payload_shape = _text(data, "payload_shape", 4000)
        if system not in EDGE_CONSTRAINTS['crm_system']['allowed_values']:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "crm_system must be one of: "
                         + ", ".join(EDGE_CONSTRAINTS['crm_system']['allowed_values']),
            }
        # An unusable destination is not a refusal here: this capability is a
        # placeholder, so an unusable value is recorded as unusable and the
        # state stays stubbed -- nothing is ever pushed to it.
        destination_valid = bool(
            destination_url and destination_url.startswith(("http://", "https://"))
        )
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    # Which systems have a live integration here? The block answers with
    # mock_unavailable for every one of them, and fabricates nothing.
    # With no CRM named there is no system to ask about: the bus is asked to
    # list what it carries, and it answers that every entry is mock_unavailable.
    # mock_connector_bus reads its action out of its own payload (its
    # input_schema declares ``action`` as a field), so it travels in
    # payload_extra -- the documented exception to action-as-a-keyword, and
    # the same shape the block's own UI sends.
    systems = runner(
        "mock_connector_bus",
        {"system": system if system in _BUS_SYSTEMS else "opera"},
        action="systems",
        payload_extra={"action": "systems"},
    )
    available = (
        systems.get("available") if isinstance(systems, dict) else None
    )
    live_systems = [
        key for key in (systems.get("systems") or [])
        if isinstance(key, dict) and key.get("mock_level") != "mock_unavailable"
    ] if isinstance(systems, dict) else []

    registered = runner(
        "webhook",
        {
            "name": f"crm-{system}",
            "url": destination_url or "https://crm.invalid/unstated",
            "events": ["call.outcome", "call.transferred"],
            "payload": PAYLOAD_SHAPE,
        },
        action="register",
    )
    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    named = system != "unstated"
    delivery_state = "queued" if (named and registered.get("registered")) else "stubbed"

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "crm_system": system,
        "delivery_state": delivery_state,
        "mock_mode": True,
        "integration_status": "placeholder",
        "blocker": "" if named else (
            "crm_destination_unstated: no CRM destination was named, so call "
            "outcome and broker summary are recorded and not pushed"
        ),
        "destination_url_valid": destination_valid,
        "destination_registered": bool(registered.get("registered"))
        if isinstance(registered, dict) else False,
        "available_systems": [
            item.get("system") for item in (systems.get("systems") or [])
            if isinstance(item, dict)
        ] if isinstance(systems, dict) else [],
        "live_systems": live_systems,
        "fabricated_data": False,
        "payload_shape": payload_shape or PAYLOAD_SHAPE,
        "declared_block_unavailable": ["mock_connector_bus"] if available is False else [],
        "blocks": runner.report(),
    }
