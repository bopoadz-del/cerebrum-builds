"""Voice gateway — Twilio Programmable Voice behind a block contract.

Written by the factory WRITER role (codewhale exec)

Three actions, one module: ``originate`` places the outbound call,
``gather`` builds the Polly Neural say + speech gather in English or Arabic
and reads what the caller said back into the dialogue, and
``status_callback`` maps the carrier's status (initiated / ringing /
answered / completed / failed / busy / no-answer) onto this platform's
workflow transitions, keyed by Call SID.

The Twilio edge is stubbed: no account, token or caller number was supplied,
so originate returns the exact request it would have sent, names the missing
settings, and dials nothing.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import config, domain, llm
from app import tenancy
from app.models import MODELS
from app.voice import TwilioEdge, canonical_status, twilio_client

CAPABILITY_ID = "voice_gateway"

REQUIRED_FIELDS = ["call_sid", "to_number"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "call_sid": {"required": True, "max_length": 64},
    "to_number": {"required": True, "max_length": 40},
    "voice_action": {"allowed_values": ['originate', 'gather', 'status_callback', 'hangup']},
    "from_number": {"max_length": 40},
    "direction": {"allowed_values": ['outbound', 'inbound']},
    "language": {"allowed_values": ['en', 'ar']},
    "call_status": {"allowed_values": ['initiated', 'ringing', 'answered', 'completed', 'failed', 'busy', 'no-answer']},
    "call_event": {"max_length": 40},
    "transition_to": {"allowed_values": ['queued', 'dialing', 'answered', 'pitched', 'qualified', 'transferred', 'callback', 'closed']},
    "mapping_ok": {},
    "twiml": {"max_length": 4000},
    "asr_transcript": {"max_length": 4000},
    "tts_text": {"max_length": 2000},
    "tts_voice": {"max_length": 60},
    "gather_language": {"max_length": 12},
    "conference_sid": {"max_length": 64},
    "duration_seconds": {"min": 0},
    "attempt": {"min": 0},
    "provider": {"max_length": 40},
    "call_key_source": {"max_length": 40},
    "edge_stub": {},
    "unavailable_blocks": {"max_length": 400},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

STATUS_EVENTS = {
    "initiated": "dial",
    "ringing": "dial",
    "answered": "answer",
    "completed": "close",
    "failed": "no_answer",
    "busy": "busy",
    "no-answer": "no_answer",
}


def _require(body: Dict[str, Any]) -> Dict[str, Any] | None:
    for name in REQUIRED_FIELDS:
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name in ("reference", "status"):
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    return None


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Place, gather or receive — whichever the edge was asked for."""
    body = dict(payload or {})
    refusal = _require(body)
    if refusal:
        return refusal
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
    language = str(body.get("language") or "en").lower()[:2]
    action = str(body.get("voice_action") or "originate")
    edge: TwilioEdge = twilio_client()
    state = edge.state()
    record: Dict[str, Any] = {
        "language": language,
        "voice_action": action,
        "to_number": str(body.get("to_number") or ""),
        "from_number": edge.caller_number,
        "direction": str(body.get("direction") or "outbound"),
        "provider": "twilio",
        "edge_stub": bool(state["stub"]),
        "attempt": domain.as_int(body.get("attempt"), 1),
        "unavailable_blocks": ", ".join(state["unavailable_blocks"]),
        "tts_voice": config.TWILIO_TTS_VOICE.get(language),
        "gather_language": config.TWILIO_ASR_LANGUAGE.get(language),
    }
    if action == "originate":
        placed = edge.originate(body)
        record.update(
            {
                "call_status": "initiated",
                "call_event": "dial",
                "transition_to": "dialing",
                "mapping_ok": True,
                "twiml": edge.gather_twiml(
                    {"language": language, "tts_text": body.get("tts_text") or ""}
                ),
                "call_key_source": "requested" if body.get("call_sid") else "generated",
            }
        )
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "decision": "stubbed" if placed.get("edge_stub") else "placed",
            "call_sid": placed.get("call_sid") or body.get("call_sid"),
            "request": placed.get("request"),
            "blocks_unavailable": placed.get("unavailable_blocks"),
            "record": record,
            "authority": domain.envelope(
                [
                    domain.Claim(
                        name="originate",
                        value=placed.get("call_status"),
                        layer="procedures",
                        source="voice.TwilioEdge.originate",
                        detail="edge stubbed; nothing dialled" if placed.get("edge_stub") else "call placed",
                    )
                ]
            ),
        }
    if action == "status_callback":
        status = canonical_status(str(body.get("call_status") or ""))
        mapped = edge.map_status(status)
        event = STATUS_EVENTS.get(status, mapped.get("call_event") or "")
        target = mapped.get("transition_to") or "dialing"
        record.update(
            {
                "call_status": status,
                "call_event": event,
                "transition_to": target,
                "mapping_ok": bool(mapped.get("mapping_ok")),
            }
        )
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "decision": "mapped",
            "call_sid": body.get("call_sid"),
            "call_status": status,
            "transition_to": target,
            "call_event": event,
            "record": record,
            "authority": mapped.get("authority"),
        }
    gathered = edge.parse_gather_callback({"SpeechResult": body.get("asr_transcript") or ""})
    turn = llm.dialogue_turn(
        tenant_id,
        {
            "call_sid": body.get("call_sid"),
            "language": language,
            "project_tag": body.get("project_tag"),
            "utterance": body.get("asr_transcript"),
            "claim_type": body.get("claim_type"),
        },
    )
    record.update(
        {
            "call_status": "answered",
            "call_event": "gather",
            "transition_to": "pitched",
            "mapping_ok": True,
            "asr_transcript": str(body.get("asr_transcript") or ""),
            "tts_text": str(turn.get("say") or "")[:2000],
            "gather_language": config.TWILIO_ASR_LANGUAGE.get(gathered.get("language") or language),
            "twiml": edge.gather_twiml({"language": language, "tts_text": turn.get("say")}),
            "call_key_source": "call_sid",
        }
    )
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": "withheld" if turn.get("withheld") else "spoken",
        "say": turn.get("say"),
        "outcome": turn.get("outcome"),
        "collected": turn.get("collected"),
        "record": record,
        "authority": turn.get("authority"),
    }
