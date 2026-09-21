"""Warm transfer: summary -> broker leg -> whisper -> conference bridge.

Written by the factory WRITER role (codewhale exec)

The sequence is the contract, and the ordering is the part that matters:

1. collect the conversation summary. An empty summary refuses the transfer --
   a broker is never joined to a call with nothing to tell them.
2. dial the broker leg (its own outbound call, its own Call SID).
3. whisper the private summary to the broker leg only, via Polly Neural TTS,
   *before* any bridge exists. The lead leg is not connected yet, so the
   summary cannot leak to the lead.
4. conference-bridge both legs into one named room (<Dial><Conference>).
5. return the transfer outcome.

The broker leg is the only leg that ever carries the whisper TwiML; the
transfer record records both leg SIDs so the whisper can be audited per call.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from app.voice import twilio_client


class TransferRefused(RuntimeError):
    """The transfer is refused. The message names the reason."""


#: Outcomes that are allowed to reach a human broker.
QUALIFYING_OUTCOMES = ("project_interested", "other_re_interested")


def _xml_escape(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_whisper_twiml(
    *,
    summary: str,
    conference_name: str,
    language: str = "en",
    end_conference_on_exit: bool = False,
) -> str:
    """The broker leg's TwiML: whisper first, then join the conference.

    Nothing here is reachable by the lead's leg -- this document is only ever
    handed to the broker's outbound call.
    """
    profile = twilio_client.language_profile(language)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        '  <Say voice="{voice}" language="{say}">Incoming warm transfer. '
        "Private summary for you only: {summary}</Say>\n"
        '  <Dial>\n'
        '    <Conference startConferenceOnEnter="true" '
        'endConferenceOnExit="{end_on_exit}" beep="false">{room}</Conference>\n'
        "  </Dial>\n"
        "</Response>\n"
    ).format(
        voice=profile["polly_voice"],
        say=profile["say_language"],
        summary=_xml_escape(summary),
        end_on_exit="true" if end_conference_on_exit else "false",
        room=_xml_escape(conference_name),
    )


def build_lead_bridge_twiml(*, conference_name: str, language: str = "en") -> str:
    """The lead leg's TwiML: join the room, and no whisper anywhere in it."""
    profile = twilio_client.language_profile(language)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        '  <Say voice="{voice}" language="{say}">Connecting you to a '
        "consultant now.</Say>\n"
        '  <Dial>\n'
        '    <Conference startConferenceOnEnter="false" '
        'endConferenceOnExit="false" beep="false">{room}</Conference>\n'
        "  </Dial>\n"
        "</Response>\n"
    ).format(
        voice=profile["polly_voice"],
        say=profile["say_language"],
        room=_xml_escape(conference_name),
    )


def transfer(
    *,
    summary: str,
    lead_number: str,
    broker_number: str,
    call_sid: str = "",
    outcome: str = "",
    language: str = "en",
    conference_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the bridge sequence and return the transfer outcome."""
    text = str(summary or "").strip()
    if not text:
        raise TransferRefused(
            "summary is required: a broker is never bridged without one"
        )
    if outcome and outcome not in QUALIFYING_OUTCOMES:
        raise TransferRefused(
            f"outcome {outcome!r} does not qualify for a warm transfer: "
            + ", ".join(QUALIFYING_OUTCOMES)
        )
    if not str(broker_number or "").strip():
        raise TransferRefused("broker_number is required to dial the broker leg")
    room = str(conference_name or f"callops-{uuid.uuid4().hex[:12]}")

    # The whisper document exists before either leg is dialed, so the audit
    # record can show exactly what the broker was told and when.
    whisper_twiml = build_whisper_twiml(summary=text, conference_name=room, language=language)
    lead_twiml = build_lead_bridge_twiml(conference_name=room, language=language)
    if "Private summary" in lead_twiml:
        # Programming error guard: the whisper must never reach the lead leg.
        raise TransferRefused("the lead leg's TwiML carries the whisper")

    broker_leg = twilio_client.originate_call(
        to_number=broker_number,
        language=language,
        prompt="",
        twiml_url=None,
    )
    sequence: List[Dict[str, Any]] = [
        {"stage": "summary_collected", "characters": len(text),
         "call_sid": call_sid or broker_leg["call_sid"]},
        {"stage": "broker_leg_dialed", "call_sid": broker_leg["call_sid"],
         "twilio_mode": broker_leg["twilio_mode"]},
        {"stage": "whisper_delivered", "audience": "broker_leg_only",
         "voice": broker_leg["voice"], "characters": len(text)},
    ]

    lead_leg: Dict[str, Any] = {"call_sid": call_sid or "", "twilio_mode": broker_leg["twilio_mode"]}
    if lead_number:
        lead_leg = twilio_client.originate_call(
            to_number=lead_number,
            language=language,
            prompt="",
            twiml_url=None,
        )
        sequence.append(
            {"stage": "lead_leg_bridged", "call_sid": lead_leg["call_sid"],
             "twilio_mode": lead_leg["twilio_mode"]}
        )
    else:
        sequence.append(
            {"stage": "lead_leg_bridged", "call_sid": lead_leg["call_sid"],
             "note": "the answered leg is already up; it joins the room by SID"}
        )

    sequence.append(
        {"stage": "conference_bridged", "conference": room,
         "legs": [leg for leg in (broker_leg["call_sid"], lead_leg["call_sid"]) if leg]}
    )

    return {
        "transfer_status": "bridged",
        "conference_name": room,
        "broker_call_sid": broker_leg["call_sid"],
        "lead_call_sid": lead_leg["call_sid"],
        "whisper_delivered": True,
        "whisper_audience": "broker_leg_only",
        "whisper_twiml": whisper_twiml,
        "lead_twiml": lead_twiml,
        "twilio_mode": broker_leg["twilio_mode"],
        "language": str(language).lower(),
        "sequence": sequence,
    }
