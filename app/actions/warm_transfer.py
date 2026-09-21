"""Handler for capability warm_transfer.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — this repository.

On a qualifying outcome the lead is handed to a human broker: collect the
conversation summary, dial the broker leg, whisper the private summary to the
broker leg only via Polly Neural TTS, conference-bridge both legs, and return
the transfer outcome. The ordering is enforced in app/voice/warm_transfer.py,
not described in prose: the whisper is spoken before any bridge exists, so it
cannot leak to the lead, and the lead leg's TwiML is asserted free of it.

A transfer is refused -- not faked -- when the outcome does not qualify, when
the summary is empty, or when no broker number is configured. Every accepted
transfer publishes ``call.transferred`` on the event bus.

Scope
-----
READS  this capability's own columns from the caller's record; the Twilio
       settings from the process environment (via app.voice.twilio_client);
       the recorded fake-Twilio fixtures under tests/fixtures/twilio/.
WRITES the broker and lead originate requests and the two twiml documents;
       exactly one row in ``warm_transfer`` via the ROUTE's
       ``store.save(entity, record, tenant_id)`` -- this handler has no
       tenant and never persists directly; one ``call.transferred`` event.
NEVER  dialing when the transport is stubbed; bridging a broker with no
       summary; putting the whisper on the lead's leg; unguarded network
       egress; ``vendor/**`` (sealed, read-only); another capability's table.

The Twilio edge is stubbed until an account and a caller number exist: with
``TWILIO_ACCOUNT_SID`` / ``TWILIO_AUTH_TOKEN`` / ``TWILIO_CALLER_NUMBER``
unset the legs are dialed against the recorded fake-Twilio transport and no
socket is opened.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text
from app.voice import twilio_client, warm_transfer as bridge

CAPABILITY_ID = "warm_transfer"
ENTITY = "warm_transfer"
#: The bridge sequence is authored logic (app/voice/warm_transfer.py); the
#: event bus carries the outcome so the call state machine sees it.
BLOCK_IDS: List[str] = ['event_bus']
BLOCK_DEFAULT_ACTIONS = {'event_bus': 'publish'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'call_sid', 'lead_name', 'outcome', 'broker_number',
    'conference_name', 'summary', 'whisper_text', 'transfer_status',
    'whisper_delivered', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'call_sid': {'required': True},
    'outcome': {'allowed_values': list(bridge.QUALIFYING_OUTCOMES) + ['not_interested'],
                'required': True},
    'transfer_status': {'allowed_values': ['initiated', 'bridged', 'failed', 'declined'],
                        'required': False},
}


def _text(data: Dict[str, Any], name: str, limit: int = 4000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def configured_broker_number() -> str:
    """The broker leg's number, from the operator's environment.

    A named setting with no default: the platform does not choose a broker
    line on the customer's behalf, and an unset value is reported by name
    rather than guessed.
    """
    return str(os.environ.get("BROKER_TRANSFER_NUMBER") or "").strip()


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "transfer"
        call_sid = _text(data, "call_sid", 80)
        lead_name = _text(data, "lead_name", 200)
        outcome = _text(data, "outcome", 40).lower()
        broker_number = _text(data, "broker_number", 40)
        conference_name = _text(data, "conference_name", 80)
        summary = _text(data, "summary", 2000)
        whisper_text = _text(data, "whisper_text", 2000)
        if outcome and outcome not in bridge.QUALIFYING_OUTCOMES and outcome != "not_interested":
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "outcome must be one of: "
                         + ", ".join(bridge.QUALIFYING_OUTCOMES + ("not_interested",)),
            }
        if outcome == "not_interested":
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "not_interested does not qualify for a warm transfer: "
                         "the lead is closed and suppressed instead",
                "transfer_status": "declined",
                "call_sid": call_sid,
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    # The broker is told the qualification and the collected fields; the
    # whisper is the private summary and nothing else travels on that leg.
    brief = summary or (
        f"{lead_name or 'Lead'} is qualified ({outcome or 'project_interested'}) "
        f"on call {call_sid or 'unkeyed'}."
    )
    # The broker leg's number is the caller's when supplied, else the
    # operator's BROKER_TRANSFER_NUMBER. With neither, there is no leg to
    # dial: the transfer is DECLINED by name (the record is still valid and
    # the summary is still recorded for whoever picks the lead up) rather
    # than refused, which would report a valid record as a bad request.
    broker_number = broker_number or configured_broker_number()
    if not broker_number:
        published = runner(
            "event_bus",
            {
                "topic": "call.transfer_declined",
                "payload": {
                    "call_sid": call_sid,
                    "outcome": outcome or "project_interested",
                    "reason": "no_broker_number",
                },
                "message": f"warm transfer declined for {call_sid or reference}: "
                           "no broker number configured",
                "channel": "mcp",
                "tool": "event_bus",
            },
            action="publish",
        )
        refusal = runner.refusal()
        if refusal is not None:
            return {"ok": False, "capability": CAPABILITY_ID, **refusal}
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "call_sid": call_sid,
            "lead_name": lead_name,
            "outcome": outcome or "project_interested",
            "transfer_status": "declined",
            "broker_number": "",
            "conference_name": "",
            "whisper_delivered": False,
            "summary": brief,
            "blocker": (
                "no broker leg to dial: set BROKER_TRANSFER_NUMBER or send "
                "broker_number on the record"
            ),
            "event": {
                "topic": published.get("topic") if isinstance(published, dict)
                else "call.transfer_declined",
                "correlation_id": published.get("correlation_id")
                if isinstance(published, dict) else None,
            },
            "blocks": runner.report(),
        }
    try:
        result = bridge.transfer(
            summary=brief,
            lead_number="",
            broker_number=broker_number,
            call_sid=call_sid,
            outcome=outcome,
            conference_name=conference_name or None,
        )
    except (bridge.TransferRefused, twilio_client.TwilioRefused) as exc:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": str(exc),
            "transfer_status": "failed",
            "call_sid": call_sid,
        }

    topic = "call.transferred"
    published = runner(
        "event_bus",
        {
            "topic": topic,
            "payload": {
                "call_sid": call_sid,
                "broker_call_sid": result["broker_call_sid"],
                "conference": result["conference_name"],
                "outcome": outcome or "project_interested",
            },
            "message": f"warm transfer bridged for {call_sid or reference}",
            "channel": "mcp",
            "tool": "event_bus",
        },
        action="publish",
    )
    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "call_sid": call_sid,
        "lead_name": lead_name,
        "outcome": outcome or "project_interested",
        "transfer_status": result["transfer_status"],
        "conference_name": result["conference_name"],
        "broker_call_sid": result["broker_call_sid"],
        "lead_call_sid": result["lead_call_sid"],
        "whisper_delivered": result["whisper_delivered"],
        "whisper_audience": result["whisper_audience"],
        "whisper_text": whisper_text or brief,
        "twilio_mode": result["twilio_mode"],
        "sequence": result["sequence"],
        "whisper_twiml": result["whisper_twiml"],
        "event": {
            "topic": published.get("topic") if isinstance(published, dict) else topic,
            "correlation_id": published.get("correlation_id")
            if isinstance(published, dict) else None,
        },
        "blocks": runner.report(),
    }
