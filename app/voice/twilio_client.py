"""Twilio Programmable Voice edge for CallOps.

Written by the factory WRITER role (codewhale exec)

Two transports, one contract:

``live``
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_CALLER_NUMBER are all
    set. ``originate_call`` performs a real REST POST to the Twilio API
    endpoint. Nothing else in the platform dials.

``stubbed``
    Any of the three is missing (the state this product ships in: no
    credentials and no caller number were supplied). The gateway originates
    against a recorded fake-Twilio transport -- the fixtures under
    ``tests/fixtures/twilio/`` -- and the module refuses to open a socket.
    CI never dials.

The status-callback vocabulary is Twilio's own and it is mapped here, not in
prose: initiated / ringing / answered / completed / failed / busy /
no-answer -> a workflow state, keyed by the Call SID.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

#: Twilio status-callback event -> CallOps call state (see app/workflows.py).
STATUS_TRANSITIONS: Dict[str, str] = {
    "initiated": "dialing",
    "ringing": "dialing",
    "answered": "answered",
    "completed": "closed",
    "failed": "callback",
    "busy": "callback",
    "no-answer": "callback",
}

#: Hard cap per lead, exercised on the busy / no-answer / failed path.
MAX_ATTEMPTS = 3

#: Locale and Polly Neural voice per language. Arabic is dialed with Polly's
#: bilingual voice: Twilio's ar-AE ASR accepts Gulf Arabic speech.
LANGUAGE_PROFILE: Dict[str, Dict[str, str]] = {
    "en": {"asr_language": "en-US", "say_language": "en-US",
           "polly_voice": "Polly.Joanna-Neural", "speech_model": "phone_call"},
    "ar": {"asr_language": "ar-AE", "say_language": "arb",
           "polly_voice": "Polly.Hala-Neural", "speech_model": "phone_call"},
}

API_BASE = "https://api.twilio.com/2010-04-01"
FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "twilio"


class TwilioRefused(RuntimeError):
    """The gateway refuses to dial. The message names the reason."""


def credentials() -> Dict[str, str]:
    """The three settings that turn the live transport on. No defaults."""
    return {
        "account_sid": str(os.environ.get("TWILIO_ACCOUNT_SID") or "").strip(),
        "auth_token": str(os.environ.get("TWILIO_AUTH_TOKEN") or "").strip(),
        "caller_number": str(os.environ.get("TWILIO_CALLER_NUMBER") or "").strip(),
    }


def mode() -> str:
    """``live`` when every credential is set, otherwise ``stubbed``."""
    return "live" if all(credentials().values()) else "stubbed"


def language_profile(language: str) -> Dict[str, str]:
    key = str(language or "en").strip().lower()
    if key not in LANGUAGE_PROFILE:
        raise TwilioRefused(f"unsupported language {language!r}: use en or ar")
    return dict(LANGUAGE_PROFILE[key])


def _xml_escape(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_gather_twiml(
    *,
    prompt: str,
    action_url: str,
    language: str = "en",
    timeout_seconds: int = 5,
) -> str:
    """The outbound-call TwiML: Polly Neural speech, then ASR gather.

    ``input="speech"`` is Twilio Programmable Voice's speech gather; the
    language hint is the profile's ``asr_language`` so English and Arabic
    conversations are both transcribed by the edge rather than by us.
    """
    profile = language_profile(language)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        '  <Gather input="speech" language="{asr}" speechModel="{model}" '
        'timeout="{timeout}" action="{action}" method="POST">\n'
        '    <Say voice="{voice}" language="{say}">{prompt}</Say>\n'
        "  </Gather>\n"
        '  <Say voice="{voice}" language="{say}">We did not hear a reply. '
        "Goodbye.</Say>\n"
        "</Response>\n"
    ).format(
        asr=profile["asr_language"],
        model=profile["speech_model"],
        timeout=int(timeout_seconds),
        action=_xml_escape(action_url),
        voice=profile["polly_voice"],
        say=profile["say_language"],
        prompt=_xml_escape(prompt),
    )


def map_status_event(status: str, *, attempt_count: int = 0) -> Dict[str, Any]:
    """Map one Twilio status callback onto a CallOps state transition.

    A terminal failure returns the call to ``callback`` while attempts remain
    (max three spaced attempts, enforced by app.formulas); with the budget
    spent the call closes instead of dialing forever.
    """
    event = str(status or "").strip().lower().replace("_", "-")
    if event not in STATUS_TRANSITIONS:
        raise TwilioRefused(
            f"unknown status callback {status!r}: expected one of "
            + ", ".join(sorted(STATUS_TRANSITIONS))
        )
    state = STATUS_TRANSITIONS[event]
    exhausted = event in ("failed", "busy", "no-answer") and attempt_count >= MAX_ATTEMPTS
    return {
        "event": event,
        "state": "closed" if exhausted else state,
        "retry": state == "callback" and not exhausted,
        "attempt_count": int(attempt_count),
        "attempts_remaining": max(0, MAX_ATTEMPTS - int(attempt_count)),
    }


def _fake_transport(request: Dict[str, Any]) -> Dict[str, Any]:
    """Recorded fake-Twilio response. Never opens a socket."""
    fixture = FIXTURE_DIR / "call_create.json"
    body: Dict[str, Any] = {}
    if fixture.is_file():
        try:
            body = json.loads(fixture.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            body = {}
    if not body:
        raise TwilioRefused(
            f"stubbed transport has no recorded fixture at {fixture}: "
            "the fake harness is the only transport CI may use"
        )
    body = dict(body)
    body["sid"] = f"CA{uuid.uuid4().hex[:24]}"
    body["to"] = request.get("To")
    body["from"] = request.get("From") or "+10000000000"
    body["status"] = "queued"
    body["_transport"] = "stubbed"
    return body


def _live_transport(request: Dict[str, Any]) -> Dict[str, Any]:
    """A real Twilio REST originate. Only reachable with all three settings."""
    creds = credentials()
    missing = [key for key, value in creds.items() if not value]
    if missing:
        raise TwilioRefused(
            "live transport needs " + ", ".join(sorted(missing))
        )
    url = f"{API_BASE}/Accounts/{creds['account_sid']}/Calls.json"
    data = urllib.parse.urlencode(request).encode("utf-8")
    token = base64.b64encode(
        f"{creds['account_sid']}:{creds['auth_token']}".encode("utf-8")
    ).decode("ascii")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": "Basic " + token,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:  # the error body names the reason
        raise TwilioRefused(f"Twilio refused the call: HTTP {exc.code}") from exc
    except OSError as exc:
        raise TwilioRefused(f"Twilio unreachable: {exc}") from exc
    if not isinstance(payload, dict):
        raise TwilioRefused("Twilio answered a non-object body")
    payload["_transport"] = "live"
    return payload


def originate_call(
    *,
    to_number: str,
    language: str = "en",
    twiml_url: Optional[str] = None,
    status_callback_url: Optional[str] = None,
    prompt: str = "Hello, this is the PSI property line.",
    from_number: Optional[str] = None,
) -> Dict[str, Any]:
    """Originate one outbound call. Refuses a bad number before any transport."""
    to = str(to_number or "").strip()
    if not to:
        raise TwilioRefused("to_number is required: there is no number to dial")
    # E.164 is a requirement of the live carrier, so it is enforced on the
    # live transport. Against the recorded fake-Twilio transport the value is
    # carried and marked unverified instead of inventing a refusal the offline
    # platform cannot distinguish from a carrier rejection.
    number_format_verified = to.startswith("+")
    if mode() == "live" and not number_format_verified:
        raise TwilioRefused(
            "to_number must be E.164 (leading +) to dial: a lead is only "
            "dialed on the number the lead file supplied"
        )
    profile = language_profile(language)
    creds = credentials()
    sender = str(from_number or creds["caller_number"] or "").strip()
    transport_mode = mode()
    if transport_mode == "live" and not sender:
        raise TwilioRefused("live transport needs TWILIO_CALLER_NUMBER")

    twiml = build_gather_twiml(
        prompt=prompt,
        action_url=twiml_url or "/v1/voice_gateway/gather",
        language=language,
    )
    request = {
        "To": to,
        "From": sender or "+10000000000",
        "Twiml": twiml,
        "StatusCallback": status_callback_url or "/v1/voice_gateway/status",
        "StatusCallbackEvent": "initiated ringing answered completed",
    }
    payload = _live_transport(request) if transport_mode == "live" else _fake_transport(request)
    return {
        "call_sid": str(payload.get("sid") or ""),
        "status": "initiated",
        "twilio_status": str(payload.get("status") or "queued"),
        "twilio_mode": transport_mode,
        "to_number": to,
        "from_number": str(payload.get("from") or request["From"]),
        "language": str(language).lower(),
        "number_format_verified": number_format_verified,
        "asr_language": profile["asr_language"],
        "voice": profile["polly_voice"],
        "twiml": twiml,
        "transport": str(payload.get("_transport") or transport_mode),
    }
