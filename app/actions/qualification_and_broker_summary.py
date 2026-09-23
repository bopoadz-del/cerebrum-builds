"""Qualification & broker summary.

Written by the factory WRITER role (codewhale exec)

Qualification is a schema, not prose: the outcome is one value from
{project_interested, other_re_interested, not_interested}, and the fields
collected beside it (property type, budget, area, timeline) are stored, not
paraphrased. The broker summary is then built from that record — so two
brokers reading two summaries of the same call read the same thing.

The currency column is filled from the operator's CURRENCY setting when it
is set, and left empty when it is not: the brief states no country.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import config, dispatch, domain
from app import tenancy
from app.models import MODELS

CAPABILITY_ID = "qualification_and_broker_summary"

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'validation': 'record',
    'recommendation_template': 'summary',
    'knowledge': 'ingest',
    # Bound as well: the broker is pinged the moment a lead qualifies, and
    # that alert leaves through the notification block.
    'notification': 'send',
}

REQUIRED_FIELDS = ["call_sid", "outcome"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "call_sid": {"required": True, "max_length": 64},
    "outcome": {"allowed_values": ['project_interested', 'other_re_interested', 'not_interested'], "required": True},
    "language": {"allowed_values": ['en', 'ar']},
    "project_tag": {"max_length": 80},
    "lead_name": {"max_length": 160},
    "property_type": {"allowed_values": ['apartment', 'villa', 'townhouse', 'plot', 'office', 'retail', 'other']},
    "budget": {"min": 0},
    "currency": {"max_length": 8},
    "area": {"max_length": 120},
    "timeline": {"allowed_values": ['immediate', 'three_months', 'six_months', 'twelve_months', 'browsing', 'unknown']},
    "transcript": {"max_length": 4000},
    "collected": {},
    "summary": {},
    "summary_text": {"max_length": 2000},
    "recommendation": {"max_length": 600},
    "next_action": {"allowed_values": ['transfer_to_broker', 'schedule_callback', 'close_lead', 'nurture']},
    "qualified": {},
    "transfer_required": {},
    "authority_layer": {"max_length": 40},
    "authority_label": {"max_length": 200},
    "campaign": {"max_length": 80},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}


def _currency() -> str | None:
    if config.env("CURRENCY"):
        return config.currency()
    return None


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record the outcome and structured fields, and build the broker summary."""
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
    collected = domain.collect_fields(
        str(body.get("transcript") or body.get("utterance") or ""),
        {
            "property_type": body.get("property_type"),
            "budget": body.get("budget"),
            "area": body.get("area"),
            "timeline": body.get("timeline"),
        },
    )
    currency = body.get("currency") or _currency()
    summary = domain.broker_summary(
        {
            "outcome": body.get("outcome"),
            "call_sid": body.get("call_sid"),
            "project_tag": body.get("project_tag"),
            "lead_name": body.get("lead_name"),
            "language": body.get("language"),
            "currency": currency,
            **collected,
        },
        currency=currency,
    )
    # The broker is pinged the moment a lead qualifies: the alert leaves here,
    # not from a schedule someone has to remember to run. With no channel
    # configured the block records the intent and names the setting, and the
    # qualification itself still stands.
    alert: Dict[str, Any] = {"delivery": "not_required"}
    if summary["transfer_required"]:
        alert = dispatch.execute(
            "notification",
            action=BLOCK_DEFAULT_ACTIONS["notification"],
            payload={
                "trigger_event": "lead_qualified",
                "channel": "webhook",
                "subject": f"Warm lead: {body.get('project_tag') or 'project'}",
                "body": summary["summary_text"],
                "call_sid": body.get("call_sid"),
                "summary": summary["summary"],
                "tenant_id": body.get("tenant_id") or tenancy.deployment_tenant(),
            },
        )
    failure = dispatch.refusal_of(alert) if summary["transfer_required"] else None
    if failure:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "the broker alert could not be composed: " + failure,
        }
    warnings: List[str] = []
    if not currency:
        warnings.append(
            "CURRENCY is not set: the budget is recorded without a currency "
            "rather than labelled with one the operator never chose"
        )
    if not collected.get("budget"):
        warnings.append("no budget was stated on the call")
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": summary["next_action"],
        "outcome": body.get("outcome"),
        "next_action": summary["next_action"],
        "qualified": summary["qualified"],
        "transfer_required": summary["transfer_required"],
        "recommendation": summary["recommendation"],
        "summary": summary["summary"],
        "notification": {
            "delivery": alert.get("delivery"),
            "response_code": alert.get("response_code", 0),
            "channel": alert.get("channel"),
            "blocks_unavailable": alert.get("blocks_unavailable") or [],
            "note": alert.get("note") or (
                "the alert left the platform" if alert.get("delivery") == "delivered" else ""
            ),
        },
        "warnings": warnings,
        "record": {
            "language": body.get("language"),
            "project_tag": body.get("project_tag"),
            "lead_name": body.get("lead_name"),
            "property_type": collected.get("property_type"),
            "budget": collected.get("budget"),
            "currency": currency,
            "area": collected.get("area"),
            "timeline": collected.get("timeline"),
            "collected": str(collected),
            "summary": str(summary["summary"]),
            "summary_text": summary["summary_text"],
            "recommendation": summary["recommendation"],
            "next_action": summary["next_action"],
            "qualified": summary["qualified"],
            "transfer_required": summary["transfer_required"],
            "authority_layer": (summary["authority"] or {}).get("layer"),
            "authority_label": (summary["authority"] or {}).get("label"),
        },
        "authority": summary["authority"],
    }
