"""CRM destination placeholder.

Written by the factory WRITER role (codewhale exec)

The brief does not name a CRM, so nothing here claims an integration. The
handler records the outcome and the broker summary, builds the exact payload
shape a connector would send, and reports ``placeholder`` with the missing
setting named. Set CRM_DESTINATION and the same call reports ``activated``
with the shaped record ready — the connector is still not built, and it says
so rather than pretending.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import config, domain
from app.models import MODELS

CAPABILITY_ID = "crm_destination_placeholder"

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'mock_connector_bus': 'shape',
    'webhook': 'post',
}

REQUIRED_FIELDS = ["call_sid"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "call_sid": {"required": True, "max_length": 64},
    "crm_system": {"max_length": 60},
    "destination": {"max_length": 200},
    "destination_named": {},
    "payload_shape": {},
    "delivery": {"allowed_values": ['placeholder', 'activated', 'blocked', 'unavailable']},
    "unavailable_blocks": {"max_length": 400},
    "outcome": {"allowed_values": ['project_interested', 'other_re_interested', 'not_interested', 'none']},
    "summary": {},
    "note": {"max_length": 400},
    "intended_method": {"allowed_values": ['POST', 'PUT', 'PATCH']},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

KNOWN_CRMS = ("salesforce", "hubspot", "zoho", "dynamics", "pipedrive")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record what would be sent, and refuse to claim it was."""
    body = dict(payload or {})
    for name in REQUIRED_FIELDS:
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name in ("reference", "status"):
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name, rules in constraints.items():
        values = rules.get("allowed_values") or ()
        value = body.get(name)
        if value is None or value == "":
            continue
        if values and value not in values:
            return {
                "ok": False,
                "error": f"{name} must be one of: " + ", ".join(str(v) for v in values),
            }
    destination = body.get("destination") or config.CRM_DESTINATION
    system = str(body.get("crm_system") or "").strip().lower()
    if not system and destination:
        system = next((name for name in KNOWN_CRMS if name in str(destination).lower()), "")
    # An unfamiliar CRM name is recorded as given: the brief names no CRM, so
    # refusing a name this platform has not heard of would be inventing a
    # vocabulary the operator never agreed to.
    recognised = bool(system) and system in KNOWN_CRMS
    # A destination is an address. Anything else is a placeholder name, and
    # pretending it is reachable is the failure this capability exists to avoid.
    looks_like_an_address = bool(destination) and " " not in str(destination) and (
        "." in str(destination) or str(destination).startswith("http")
    )
    named = looks_like_an_address
    shape = domain.crm_payload_shape(
        call_sid=str(body.get("call_sid")),
        outcome=body.get("outcome"),
        summary=body.get("summary") or {},
        destination=destination,
    )
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": "activated" if named else "placeholder",
        "destination": destination,
        "destination_named": named,
        "blocks_unavailable": [] if named else ["CRM_DESTINATION"],
        "payload_shape": shape,
        "record": {
            "crm_system": system or None,
            "recognised_crm": recognised,
            "destination": destination,
            "destination_named": named,
            "payload_shape": str(shape),
            "delivery": "activated" if named else "placeholder",
            "unavailable_blocks": "" if named else "CRM_DESTINATION",
            "outcome": body.get("outcome") or "none",
            "summary": str(body.get("summary") or {}),
            "note": (
                "CRM destination named: the shaped record is ready for a connector"
                if named
                else "the brief names no CRM: intent and payload shape recorded, nothing sent"
            ),
            "intended_method": str(body.get("intended_method") or "POST"),
        },
        "authority": domain.envelope(
            [
                domain.Claim(
                    name="crm_payload",
                    value="shaped" if named else "placeholder",
                    layer="procedures",
                    source="domain.crm_payload_shape",
                    detail="no delivery is claimed on this path",
                )
            ]
        ),
    }
