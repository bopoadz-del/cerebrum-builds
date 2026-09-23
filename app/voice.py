"""The Twilio edge: Programmable Voice behind a block contract.

One outbound call is four things: originate it, gather speech in English or
Arabic, speak with Polly Neural, and map the carrier's status callbacks onto
this platform's workflow. This module builds all four.

**It ships stubbed.** No Twilio account, auth token or caller number was
supplied, so :func:`twilio_client` reports the missing settings by name and
the originate path returns the exact request it *would* send instead of
sending it. Two switches gate real traffic — credentials and
``TWILIO_ALLOW_DIALING=1`` — so a test run, a CI job or a laptop cannot dial
a stranger by accident.

Everything the edge does is exercised against a fake transport
(``RecordingTransport``): the TwiML, the request shape and the status→state
mapping are all asserted in tests, which is why the block can be certified
without an account.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Mapping, Optional
from xml.sax.saxutils import escape

from app import config, domain

TWIML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'


def _twiml(body: str) -> str:
    return f"{TWIML_HEADER}\n<Response>{body}</Response>"


#: Carrier spellings mapped onto the status vocabulary the brief names. The
#: edge reports what the carrier said; the platform speaks one set of names.
STATUS_ALIASES = {
    "in-progress": "answered",
    "in_progress": "answered",
    "queued": "initiated",
    "canceled": "failed",
    "cancelled": "failed",
    "no_answer": "no-answer",
}


def canonical_status(status: str) -> str:
    key = str(status or "").strip().lower()
    return STATUS_ALIASES.get(key, key)


class RecordingTransport:
    """A fake Twilio: records what would be sent, replays recorded replies.

    ``responses`` maps a path fragment to the canned reply body, exactly as
    the fixtures in ``tests/fixtures/`` hold them. CI never dials.
    """

    def __init__(self, responses: Optional[Mapping[str, Any]] = None) -> None:
        self.responses = dict(responses or {})
        self.requests: List[Dict[str, Any]] = []

    def post(self, url: str, payload: Mapping[str, Any], headers: Mapping[str, str]) -> Dict[str, Any]:
        self.requests.append({"url": url, "payload": dict(payload), "headers": dict(headers)})
        for fragment, reply in self.responses.items():
            if fragment in url:
                return dict(reply)
        return {"sid": "CAtest00000000000000000000000000", "status": "queued", "recorded": False}


class HttpTransport:
    """The real thing: one form-encoded POST to Twilio."""

    def post(self, url: str, payload: Mapping[str, Any], headers: Mapping[str, str]) -> Dict[str, Any]:
        if not str(url).startswith(("https://", "http://")):
            return {"error": "twilio endpoint is not an http(s) URL"}
        data = urllib.parse.urlencode(dict(payload or {})).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=dict(headers or {}), method="POST")
        try:
            # nosec B310 - only an http(s) Twilio endpoint reaches this line.
            with urllib.request.urlopen(request, timeout=15) as response:  # nosec B310 - http(s) checked above
                raw = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            return {"error": f"twilio answered HTTP {exc.code}", "detail": detail}
        except Exception as exc:  # noqa: BLE001 - an edge failure is data
            return {"error": f"twilio unreachable: {type(exc).__name__}"}
        try:
            return json.loads(raw or "{}")
        except ValueError:
            return {"error": "twilio answered a non-JSON body", "raw": raw[:400]}


class TwilioEdge:
    """Programmable Voice behind one contract the workflow can rely on."""

    def __init__(
        self,
        *,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        caller_number: Optional[str] = None,
        transport: Optional[Any] = None,
        allow_dialing: Optional[bool] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.account_sid = account_sid if account_sid is not None else config.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token if auth_token is not None else config.TWILIO_AUTH_TOKEN
        self.caller_number = caller_number if caller_number is not None else config.TWILIO_CALLER_NUMBER
        self.transport = transport or HttpTransport()
        self.base_url = (base_url or config.TWILIO_API_BASE).rstrip("/")
        if allow_dialing is None:
            allow_dialing = str(config.env("TWILIO_ALLOW_DIALING", "") or "") in ("1", "true", "yes")
        self.allow_dialing = bool(allow_dialing)

    # -- state -----------------------------------------------------------------
    def missing_settings(self) -> List[str]:
        missing = []
        if not self.account_sid:
            missing.append("TWILIO_ACCOUNT_SID")
        if not self.auth_token:
            missing.append("TWILIO_AUTH_TOKEN")
        if not self.caller_number:
            missing.append("TWILIO_CALLER_NUMBER")
        return missing

    def connected(self) -> bool:
        return not self.missing_settings()

    def live(self) -> bool:
        """Real traffic needs credentials AND an explicit operator opt-in."""
        return self.connected() and self.allow_dialing

    def state(self) -> Dict[str, Any]:
        return {
            "connected": self.connected(),
            "live": self.live(),
            "caller_number": self.caller_number,
            "missing": self.missing_settings(),
            "unavailable_blocks": self.missing_settings()
            + ([] if self.allow_dialing else ["TWILIO_ALLOW_DIALING"]),
            "stub": not self.live(),
        }

    # -- outgoing --------------------------------------------------------------
    def originate(self, body: Mapping[str, Any]) -> Dict[str, Any]:
        """Place the call, or return exactly what placing it would have sent.

        The answer and status-callback URLs come from the record only because
        the platform's own route put the operator's settings there; they are
        never taken from an inbound request.
        """
        record = dict(body or {})
        language = str(record.get("language") or "en").lower()[:2]
        to_number = str(record.get("to_number") or record.get("phone_e164") or "")
        requested_sid = str(record.get("call_sid") or "")
        url = f"{self.base_url}/Accounts/{self.account_sid or '{ACCOUNT_SID}'}/Calls.json"
        payload = {
            "To": to_number,
            "From": self.caller_number or "",
            "Url": str(record.get("answer_url") or ""),
            "StatusCallback": str(record.get("status_callback_url") or ""),
            "MachineDetection": "Enable",
        }
        state = self.state()
        out: Dict[str, Any] = {
            "ok": True,
            "provider": "twilio",
            "action": "originate",
            "to_number": to_number,
            "from_number": self.caller_number,
            "request": {"url": url, "payload": payload},
            "language": language,
            "call_sid": requested_sid or None,
            "call_status": "queued",
            "edge_stub": not self.live(),
            "unavailable_blocks": state["unavailable_blocks"],
        }
        if not self.live():
            out["note"] = (
                "Twilio edge is stubbed: "
                + ", ".join(state["unavailable_blocks"])
                + " would have to be set before this call is placed"
            )
            return out
        if not payload["Url"]:
            out["call_status"] = "failed"
            out["unavailable_blocks"] = ["TWILIO_ANSWER_URL"]
            out["note"] = (
                "no answer URL is configured (TWILIO_ANSWER_URL), so a live call "
                "could not be placed; the request shape is returned instead"
            )
            return out
        headers = {
            "Authorization": "Basic "
            + base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        reply = self.transport.post(url, payload, headers)
        out["response"] = reply
        out["call_sid"] = reply.get("sid") or requested_sid or None
        out["call_status"] = str(reply.get("status") or "queued")
        if reply.get("error"):
            out["call_status"] = "failed"
            out["ok"] = True
            out["unavailable_blocks"] = ["twilio_api_error"]
        return out

    # -- TwiML -----------------------------------------------------------------
    def gather_twiml(self, body: Mapping[str, Any]) -> str:
        """Speak the pitch with Polly Neural, then listen in en or ar."""
        record = dict(body or {})
        language = str(record.get("language") or "en").lower()[:2]
        voice = config.TWILIO_TTS_VOICE.get(language, config.TWILIO_TTS_VOICE["en"])
        asr = config.TWILIO_ASR_LANGUAGE.get(language, "en-US")
        say = escape(str(record.get("tts_text") or record.get("say") or ""))
        gather_url = escape(str(record.get("gather_action_url") or "/v1/voice/gather"))
        return _twiml(
            f'<Say voice="{escape(voice)}" language="{escape(asr)}">{say}</Say>'
            f'<Gather input="speech" speechTimeout="auto" language="{escape(asr)}" '
            f'action="{gather_url}" method="POST"></Gather>'
        )

    def whisper_twiml(self, body: Mapping[str, Any]) -> str:
        """The whisper: private to the broker leg, never to the lead."""
        record = dict(body or {})
        language = str(record.get("broker_language") or record.get("language") or "en").lower()[:2]
        voice = config.TWILIO_TTS_VOICE.get(language, config.TWILIO_TTS_VOICE["en"])
        asr = config.TWILIO_ASR_LANGUAGE.get(language, "en-US")
        whisper = escape(str(record.get("whisper_text") or ""))
        return _twiml(
            f'<Say voice="{escape(voice)}" language="{escape(asr)}">{whisper}</Say>'
        )

    def caller_leg_twiml(self, body: Mapping[str, Any]) -> str:
        """The lead's leg: straight into the shared conference.

        The lead's document never contains the whisper text, so a broker
        summary cannot leak to the person being qualified.
        """
        return self.conference_twiml(body)

    def dial_broker_twiml(self, body: Mapping[str, Any]) -> str:
        """The BROKER's leg: the private whisper, then the shared conference.

        Twilio fetches this document for the dialled broker leg, not for the
        caller: the whisper is spoken to the broker alone, and the broker
        then joins the same conference the caller is already waiting in --
        which is what makes it a bridge rather than two half-calls. The
        earlier shape emitted the whisper as a sibling of a nested ``<Dial>``
        in the caller's own document, so the lead heard the private summary
        the moment the broker leg ended, and neither party ever met in the
        conference. Do not put a ``<Say>`` of the whisper outside the broker
        leg's document; ``caller_leg_twiml`` is the lead's half.
        """
        record = dict(body or {})
        conference = escape(str(record.get("conference_name") or ""))
        whisper = escape(str(record.get("whisper_text") or ""))
        language = str(record.get("broker_language") or record.get("language") or "en").lower()[:2]
        voice = config.TWILIO_TTS_VOICE.get(language, config.TWILIO_TTS_VOICE["en"])
        asr = config.TWILIO_ASR_LANGUAGE.get(language, "en-US")
        return _twiml(
            f'<Say voice="{escape(voice)}" language="{escape(asr)}">{whisper}</Say>'
            f"<Dial><Conference startConferenceOnEnter=\"true\" endConferenceOnExit=\"false\">"
            f"{conference}</Conference></Dial>"
        )

    def conference_twiml(self, body: Mapping[str, Any]) -> str:
        record = dict(body or {})
        conference = escape(str(record.get("conference_name") or ""))
        return _twiml(
            f"<Dial><Conference startConferenceOnEnter=\"true\" endConferenceOnExit=\"false\">"
            f"{conference}</Conference></Dial>"
        )

    # -- inbound status --------------------------------------------------------
    def map_status(self, status: str, current: str = "dialing") -> Dict[str, Any]:
        """A carrier status becomes a workflow transition, keyed by Call SID."""
        carrier = str(status or "").strip().lower()
        mapped = domain.twilio_transition(carrier, current)
        return {
            "ok": True,
            "provider": "twilio",
            "carrier_status": carrier,
            "call_status": canonical_status(carrier),
            "call_event": mapped["event"],
            "transition_to": mapped["target_state"],
            "mapping_ok": mapped["mapping_ok"],
            "authority": domain.envelope(
                [
                    domain.Claim(
                        name="carrier_status",
                        value=mapped["target_state"],
                        layer="procedures",
                        source="voice.TWILIO_STATUS_EVENTS",
                    )
                ]
            )
            if hasattr(domain, "envelope")
            else None,
        }

    def parse_status_callback(self, form: Mapping[str, Any]) -> Dict[str, Any]:
        """Read a recorded Twilio status callback exactly as it arrives.

        The raw carrier spelling is kept as ``carrier_status``; the status the
        workflow sees is the canonical one the brief names.
        """
        body = {str(k): v for k, v in dict(form or {}).items()}
        sid = str(body.get("CallSid") or body.get("call_sid") or "")
        status = str(body.get("CallStatus") or body.get("call_status") or "")
        mapped = self.map_status(status)
        return {
            "call_sid": sid,
            "call_key_source": "CallSid" if body.get("CallSid") else "call_sid",
            **mapped,
            "duration_seconds": int(str(body.get("CallDuration") or 0) or 0),
            "from_number": str(body.get("From") or ""),
            "to_number": str(body.get("To") or ""),
        }

    def parse_gather_callback(self, form: Mapping[str, Any]) -> Dict[str, Any]:
        body = {str(k): v for k, v in dict(form or {}).items()}
        return {
            "call_sid": str(body.get("CallSid") or ""),
            "asr_transcript": str(body.get("SpeechResult") or ""),
            "confidence": float(str(body.get("Confidence") or 0) or 0),
            "language": "ar" if str(body.get("Language") or "").startswith("ar") else "en",
        }


def twilio_client(transport: Optional[Any] = None) -> TwilioEdge:
    return TwilioEdge(transport=transport) if transport is not None else TwilioEdge()


def fixture_status_callbacks() -> Dict[str, Any]:
    """The recorded status callbacks the fake harness replays.

    Seven statuses, exactly the set the brief names, so the webhook →
    transition mapping is exercised without a call being placed.
    """
    templates = {
        "initiated": {"CallStatus": "initiated", "CallDuration": "0"},
        "ringing": {"CallStatus": "ringing", "CallDuration": "0"},
        "answered": {"CallStatus": "in-progress", "CallDuration": "3"},
        "completed": {"CallStatus": "completed", "CallDuration": "154"},
        "failed": {"CallStatus": "failed", "CallDuration": "0"},
        "busy": {"CallStatus": "busy", "CallDuration": "0"},
        "no-answer": {"CallStatus": "no-answer", "CallDuration": "0"},
    }
    out: Dict[str, Any] = {}
    for index, (name, fields) in enumerate(templates.items(), start=1):
        out[name] = {
            "CallSid": f"CAfake{index:02d}0000000000000000000000000000",
            "AccountSid": "ACfake00000000000000000000000000",
            "From": "+10000000000",
            "To": "+971500000000",
            "Direction": "outbound-api",
            "SequenceNumber": str(index),
            **fields,
        }
    return out
