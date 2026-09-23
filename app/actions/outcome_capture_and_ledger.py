"""Outcome capture & ledger.

Written by the factory WRITER role (codewhale exec)

Every call event is appended to a hash chain per Call SID: each entry links
to its predecessor, so attempt / answer / transfer history survives a
restart and a rewritten row is detectable rather than silently believed.
``verify`` walks a Call SID's chain and names the first entry that does not
link. The row itself is written by the route, as every other capability's is.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import domain
from app import tenancy
from app.models import MODELS

CAPABILITY_ID = "outcome_capture_and_ledger"

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'audit_chain': 'verify',
    'database': 'list',
    'storage': 'list',
    'agent_state_sync': 'get',
}

REQUIRED_FIELDS = ["call_sid", "event_type"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "call_sid": {"required": True, "max_length": 64},
    "event_type": {"allowed_values": ['attempted', 'initiated', 'ringing', 'answered', 'pitched', 'qualified', 'outcome_recorded', 'transfer_started', 'transfer_completed', 'call_ended'], "required": True},
    "sequence": {"min": 1},
    "prev_hash": {"max_length": 64},
    "entry_hash": {"max_length": 64},
    "payload_digest": {"max_length": 64},
    "outcome": {"allowed_values": ['project_interested', 'other_re_interested', 'not_interested', 'none']},
    "actor": {"max_length": 80},
    "campaign": {"max_length": 80},
    "detail": {},
    "chain_ok": {},
    "verified_count": {"min": 0},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

VERIFY_EVENT = "call_ended"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Append one event to the chain, or verify the chain that exists."""
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
    tenant_id = str(body.get("tenant_id") or tenancy.deployment_tenant())
    if not tenant_id:
        # Tenancy comes from the authenticated principal, which the route
        # injects. A handler that cannot see it refuses rather than
        # assuming a tenant: defaulting here is how one brokerage ends up
        # writing into another's corpus with a valid token of its own.
        return {
            "ok": False,
            "error": "no tenant could be resolved: this deployment binds more "
            "than one operator, so tenancy comes from the authenticated "
            "principal and is never assumed by a handler",
        }
    call_sid = str(body.get("call_sid"))
    from app import store

    history = [
        row
        for row in store.list_all("outcome_capture_and_ledger", tenant_id)
        if str(row.get("call_sid") or "") == call_sid
    ]
    verifying = str(body.get("event_type")) == VERIFY_EVENT
    report = domain.verify_chain(history)
    entry = domain.append_ledger(
        tenant_id,
        call_sid=call_sid,
        event_type=str(body.get("event_type")),
        detail={
            "outcome": body.get("outcome"),
            "actor": body.get("actor") or "platform",
            "campaign": body.get("campaign"),
            "detail": body.get("detail"),
        },
        outcome=body.get("outcome"),
        actor=str(body.get("actor") or "platform"),
        campaign=body.get("campaign"),
    )
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": "verified" if verifying else "appended",
        "sequence": entry["sequence"],
        "entry_hash": entry["entry_hash"],
        "prev_hash": entry["prev_hash"],
        "chain_intact": report["intact"],
        "violations": report["violations"],
        "history_entries": report["entries"],
        "record": {
            "sequence": entry["sequence"],
            "prev_hash": entry["prev_hash"],
            "entry_hash": entry["entry_hash"],
            "payload_digest": entry["payload_digest"],
            "outcome": body.get("outcome") or "none",
            "actor": entry["actor"],
            "campaign": body.get("campaign"),
            "detail": entry["detail"],
            "chain_ok": report["intact"],
            "verified_count": report["entries"] + 1,
        },
        "authority": domain.envelope(
            [
                domain.Claim(
                    name="ledger_entry",
                    value=entry["entry_hash"][:16],
                    layer="procedures",
                    source="domain.append_ledger",
                    detail=f"sequence {entry['sequence']} for {call_sid}",
                )
            ]
        ),
    }
