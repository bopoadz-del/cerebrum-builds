"""Notification: ping the broker the moment a lead qualifies.

Written by the factory WRITER role (codewhale exec)

One live connector: a webhook the operator names (``SALES_CHANNEL_WEBHOOK``
or ``BROKER_ALERT_WEBHOOK``) receives a real HTTPS POST through the
private-address guard. With no webhook configured the alert is composed,
recorded and reported ``stubbed`` with the setting named — the platform
never reports a delivery it did not make.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Dict, List

from app import config, dispatch, domain
from app import tenancy
from app.models import MODELS

CAPABILITY_ID = "notification"

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'notification': 'send',
}

REQUIRED_FIELDS = ["trigger_event"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "trigger_event": {"allowed_values": ['lead_qualified', 'transfer_completed', 'call_failed', 'attempt_exhausted', 'campaign_summary'], "required": True},
    "channel": {"allowed_values": ['webhook', 'slack', 'sms', 'email']},
    "target": {"max_length": 300},
    "subject": {"max_length": 200},
    "body": {"max_length": 4000},
    "delivery": {"allowed_values": ['delivered', 'queued', 'stubbed', 'unavailable', 'refused']},
    "provider": {"max_length": 60},
    "attempts": {"min": 0},
    "response_code": {"min": 0},
    "delivered_at": {"max_length": 40},
    "unavailable_blocks": {"max_length": 400},
    "message_digest": {"max_length": 64},
    "summary": {},
    "outcome": {"allowed_values": ['project_interested', 'other_re_interested', 'not_interested', 'none']},
    "call_sid": {"max_length": 64},
    "campaign": {"max_length": 80},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

SUBJECTS = {
    "lead_qualified": "Warm lead qualified",
    "transfer_completed": "Broker bridge completed",
    "call_failed": "Call failed",
    "attempt_exhausted": "Attempts exhausted",
    "campaign_summary": "Campaign summary",
}


def _body_for(trigger: str, body: Dict[str, Any]) -> str:
    summary = body.get("summary")
    outcome = body.get("outcome")
    if not outcome and isinstance(summary, dict):
        outcome = summary.get("outcome") or (summary.get("summary") or {}).get("outcome")
    collected = ""
    if isinstance(summary, dict):
        fields = summary.get("collected") or {}
        collected = ", ".join(
            f"{key}={value}" for key, value in fields.items() if value not in (None, "")
        )
    parts = [
        f"{SUBJECTS.get(trigger, trigger)} for project {body.get('project_tag') or 'unstated'}",
        f"call {body.get('call_sid') or 'unstated'}",
        f"outcome {outcome or 'unclassified'}",
        f"lead {body.get('lead_name') or 'unnamed'}",
    ]
    if collected:
        parts.append(f"collected {collected}")
    if body.get("transfer_outcome"):
        parts.append(f"transfer {body['transfer_outcome']}")
    return "; ".join(parts)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compose the alert and actually deliver it, or say why it was not."""
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
    trigger = str(body.get("trigger_event"))
    channel = str(body.get("channel") or "webhook")
    text = str(body.get("body") or body.get("message") or "") or _body_for(trigger, body)
    subject = str(body.get("subject") or SUBJECTS.get(trigger, trigger))
    target = str(body.get("target") or config.BROKER_ALERT_WEBHOOK or "")
    outcome = dispatch.execute(
        "notification",
        action=BLOCK_DEFAULT_ACTIONS["notification"],
        payload={
            "trigger_event": trigger,
            "channel": channel,
            "target": target,
            "subject": subject,
            "body": text,
            "call_sid": body.get("call_sid"),
            "summary": body.get("summary") or {},
            "tenant_id": body.get("tenant_id") or tenancy.deployment_tenant(),
        },
    )
    failure = dispatch.refusal_of(outcome)
    if failure:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "the alert could not be composed: " + failure,
        }
    delivery = str(outcome.get("delivery") or "stubbed")
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": delivery,
        "delivery": delivery,
        "response_code": domain.as_int(outcome.get("response_code"), 0),
        "blocks_unavailable": outcome.get("blocks_unavailable") or [],
        "record": {
            "channel": channel,
            "target": target or None,
            "subject": subject,
            "body": text[:4000],
            "delivery": delivery,
            "provider": outcome.get("provider") or "none",
            "attempts": 1,
            "response_code": domain.as_int(outcome.get("response_code"), 0),
            "delivered_at": domain.utc_now() if delivery == "delivered" else None,
            "unavailable_blocks": ", ".join(outcome.get("blocks_unavailable") or []),
            "message_digest": sha256(text.encode("utf-8")).hexdigest(),
            "call_sid": body.get("call_sid"),
            "campaign": body.get("campaign"),
        },
        "authority": domain.envelope(
            [
                domain.Claim(
                    name="notification_delivery",
                    value=delivery,
                    layer="procedures",
                    source="dispatch.notification",
                    detail="real POST through the egress guard"
                    if delivery == "delivered"
                    else "no webhook configured; recorded only",
                )
            ]
        ),
    }
