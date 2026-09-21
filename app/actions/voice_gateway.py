"""Handler for capability voice_gateway.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — this repository.

The Twilio Programmable Voice edge. Originates an outbound call, builds the
Gather-speech twiml in English or Arabic with a Polly Neural voice, and maps
each Twilio status callback (initiated / ringing / answered / completed /
failed / busy / no-answer) onto a CallOps call state keyed by the Call SID.
Every transition it decides is published on the event bus so the call state
machine records why the call moved.

This capability binds no Store block: the voice edge is new code
(app/voice/twilio_client.py). The Twilio transport itself is stubbed until an
account and a caller number exist -- ``TWILIO_ACCOUNT_SID``,
``TWILIO_AUTH_TOKEN`` and ``TWILIO_CALLER_NUMBER`` are read from the
environment with no defaults, and with any of them unset the gateway runs
against the recorded fake-Twilio fixtures and refuses to open a socket.

Scope
-----
READS  this capability's own columns from the caller's record; the Twilio
       settings from the process environment (never a literal); the recorded
       fake-Twilio fixtures under tests/fixtures/twilio/.
WRITES the originate request and the twiml it hands to the carrier; exactly
       one row in ``voice_gateway`` via the ROUTE's ``store.save(entity,
       record, tenant_id)`` -- this handler has no tenant and never persists
       directly; one ``call.<state>`` event per accepted status callback.
NEVER  dialing when the transport is stubbed; unguarded network egress;
       ``vendor/**`` (sealed, read-only); another capability's table;
       ``tests/**`` (read-only fixtures only).

Runtime failures (a refused number, an unknown status callback) are answered
as a refusal envelope, never as an invented success.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text
from app.voice import twilio_client

CAPABILITY_ID = "voice_gateway"
ENTITY = "voice_gateway"
#: The voice edge is authored logic, not a Store block. The one block it
#: binds is the event bus: a status callback is a state transition, and the
#: transition is published where the rest of the platform can see it.
BLOCK_IDS: List[str] = ['event_bus']
BLOCK_DEFAULT_ACTIONS = {'event_bus': 'publish'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'call_sid', 'direction', 'to_number', 'from_number',
    'language', 'voice', 'asr_engine', 'twilio_mode', 'call_status', 'twiml',
    'recording_url', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'direction': {'allowed_values': ['outbound', 'inbound'], 'required': False},
    'language': {'allowed_values': ['en', 'ar'], 'required': True},
    'call_status': {'allowed_values': list(twilio_client.STATUS_TRANSITIONS),
                    'required': False},
}

#: ASR + TTS engine names recorded on the row so a call can be reconstructed.
ASR_ENGINE = "twilio_gather_speech"
VOICE_ENGINE = "polly_neural"


def _text(data: Dict[str, Any], name: str, limit: int = 4000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def _int(data: Dict[str, Any], name: str, default: int = 0) -> int:
    raw = data.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "call"
        direction = _text(data, "direction", 20).lower() or "outbound"
        language = _text(data, "language", 8).lower() or "en"
        to_number = _text(data, "to_number", 40)
        call_status = _text(data, "call_status", 40).lower().replace("_", "-")
        attempt_count = _int(data, "attempt_count", 0)
        if direction not in ("outbound", "inbound"):
            return {"ok": False, "capability": CAPABILITY_ID,
                    "error": "direction must be outbound or inbound"}
        if language not in twilio_client.LANGUAGE_PROFILE:
            return {"ok": False, "capability": CAPABILITY_ID,
                    "error": "language must be one of: en, ar"}
        if not (to_number or call_status):
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "to_number (to originate) or call_status (a status "
                         "callback) is required: there is nothing to do",
            }
        if call_status and call_status not in twilio_client.STATUS_TRANSITIONS:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "call_status must be one of: "
                         + ", ".join(sorted(twilio_client.STATUS_TRANSITIONS)),
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    if not call_status:
        # An originate request. twilio_client raises rather than inventing a
        # SID, so a refused number is a refusal here too.
        try:
            originated = twilio_client.originate_call(
                to_number=to_number,
                language=language,
                prompt=(_text(data, "notes", 500)
                        or "Hello, this is the PSI property line."),
            )
        except twilio_client.TwilioRefused as exc:
            return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}
        call_sid = originated["call_sid"]
        call_key_source = "call_sid"
        call_status = "initiated"
        twiml = originated["twiml"]
        twilio_mode = originated["twilio_mode"]
        voice = originated["voice"]
        asr = ASR_ENGINE
    else:
        # A status callback. The transition is keyed to the carrier's Call
        # SID when the caller supplies one; when the record carries no SID
        # -- an operator-entered state, or a fixture replayed without one --
        # the record's own reference is the correlation key. No SID is ever
        # minted here: ``call_key_source`` says which key was used, so a
        # consumer can tell a carrier-keyed transition from a
        # reference-keyed one.
        call_sid = _text(data, "call_sid", 80)
        call_key_source = "call_sid" if call_sid else "reference"
        call_sid = call_sid or reference
        twiml = _text(data, "twiml", 4000)
        twilio_mode = _text(data, "twilio_mode", 20) or twilio_client.mode()
        voice = _text(data, "voice", 60) or twilio_client.LANGUAGE_PROFILE[language]["polly_voice"]
        asr = _text(data, "asr_engine", 60) or ASR_ENGINE

    transition = twilio_client.map_status_event(call_status, attempt_count=attempt_count)
    topic = f"call.{transition['state']}"
    published = runner(
        "event_bus",
        {
            "topic": topic,
            "payload": {
                "call_sid": call_sid,
                "event": transition["event"],
                "state": transition["state"],
                "retry": transition["retry"],
            },
            "message": f"twilio {transition['event']} -> {transition['state']} "
                       f"for {call_sid}",
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
        "call_key_source": call_key_source,
        "direction": direction,
        "to_number": to_number,
        "language": language,
        "asr_engine": asr,
        "voice": voice,
        "voice_engine": VOICE_ENGINE,
        "twilio_mode": twilio_mode,
        "call_status": call_status,
        "twiml": twiml,
        "transition": transition,
        "event": {
            "topic": published.get("topic") if isinstance(published, dict) else topic,
            "correlation_id": published.get("correlation_id")
            if isinstance(published, dict) else None,
        },
        "blocks": runner.report(),
    }
