"""The Twilio edge, certified against the fake harness. CI never dials."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app import config, domain
from app.voice import RecordingTransport, TwilioEdge, twilio_client
from tests.callops_helpers import client  # noqa: F401 - the client fixture

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _callbacks() -> dict:
    return json.loads((FIXTURES / "twilio_status_callbacks.json").read_text())["callbacks"]


def _edge(**kwargs) -> TwilioEdge:
    return TwilioEdge(
        account_sid=kwargs.get("account_sid", "ACfake"),
        auth_token=kwargs.get("auth_token", "token"),
        caller_number=kwargs.get("caller_number", "+10000000000"),
        transport=kwargs.get("transport") or RecordingTransport(),
        allow_dialing=kwargs.get("allow_dialing", False),
        base_url=kwargs.get("base_url", "https://api.twilio.com/2010-04-01"),
    )


def test_the_edge_ships_stubbed_and_names_what_is_missing():
    edge = twilio_client()
    state = edge.state()
    assert state["connected"] is False
    assert state["stub"] is True
    assert set(state["missing"]) == {"TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_CALLER_NUMBER"}
    placed = edge.originate({"to_number": "+971500000000", "language": "en"})
    assert placed["edge_stub"] is True
    assert placed["call_sid"] is None
    assert "Calls.json" in placed["request"]["url"]
    assert placed["request"]["payload"]["To"] == "+971500000000"
    assert "stubbed" in placed["note"]


def test_originate_without_the_dialing_opt_in_still_sends_nothing():
    transport = RecordingTransport()
    edge = _edge(transport=transport, allow_dialing=False)
    edge.originate({"to_number": "+971500000000"})
    assert transport.requests == [], "credentials alone must not place a call"


def test_originate_with_the_opt_in_uses_the_recorded_transport():
    transport = RecordingTransport(
        {"Calls.json": json.loads((FIXTURES / "twilio_originate_response.json").read_text())}
    )
    edge = _edge(transport=transport, allow_dialing=True)
    placed = edge.originate(
        {"to_number": "+971500000000", "answer_url": "https://example.test/answer"}
    )
    assert len(transport.requests) == 1
    assert placed["call_sid"] == "CAfake01000000000000000000000000"
    assert placed["edge_stub"] is False
    headers = transport.requests[0]["headers"]
    assert headers["Authorization"].startswith("Basic ")


def test_gather_twiml_speaks_with_polly_and_listens_in_the_callers_language():
    edge = _edge()
    english = edge.gather_twiml({"language": "en", "tts_text": "Hello"})
    arabic = edge.gather_twiml({"language": "ar", "tts_text": "مرحبا"})
    assert "Polly.Joanna-Neural" in english
    assert 'language="en-US"' in english
    assert "<Gather" in english and 'input="speech"' in english
    assert "Polly.Hala-Neural" in arabic
    assert 'language="ar-SA"' in arabic


def test_every_recorded_status_callback_maps_onto_a_workflow_transition():
    edge = _edge()
    seen = {}
    for name, callback in _callbacks().items():
        parsed = edge.parse_status_callback(callback)
        assert parsed["mapping_ok"] is True, name
        assert parsed["call_sid"] == callback["CallSid"]
        assert parsed["transition_to"] in domain.STATE_SEQUENCE
        seen[name] = parsed["transition_to"]
    assert seen == {
        "initiated": "dialing",
        "ringing": "dialing",
        "answered": "answered",
        "completed": "closed",
        "failed": "callback",
        "busy": "callback",
        "no-answer": "callback",
    }


def test_a_recorded_callback_drives_the_route_and_the_ledger(client):
    from tests.callops_helpers import AUTH

    callback = _callbacks()["answered"]
    response = client.post("/v1/voice/status-callback", json=callback, headers=AUTH)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["call_sid"] == callback["CallSid"]
    assert body["call_status"] == "answered"
    assert body["transition_to"] == "answered"
    assert body["ledger"]["event_type"] == "answered"
    history = client.get(f"/v1/calls/{callback['CallSid']}", headers=AUTH)
    assert history.status_code == 200
    assert history.json()["history"]["chain"]["intact"] is True


def test_the_whisper_goes_to_the_broker_leg_only():
    """The lead's document never carries the broker summary, and both legs
    end up in the same conference — a bridge, not two half-calls.

    The earlier shape put the whisper in the caller's own TwiML as a sibling
    of a nested <Dial>, so the lead heard the private summary as soon as the
    broker leg ended. This asserts the confidentiality the brief asked for
    and the bridge that warm transfer promises.
    """
    edge = _edge()
    body = {
        "broker_number": "+971509998888",
        "broker_language": "en",
        "whisper_text": "Warm lead on the line. Outcome project_interested.",
        "conference_name": "callops-CA1",
    }
    broker_leg = edge.dial_broker_twiml(body)
    caller_leg = edge.caller_leg_twiml(body)
    assert "Warm lead on the line" in broker_leg
    assert "<Conference" in broker_leg
    assert broker_leg.index("Warm lead") < broker_leg.index("<Conference")
    # the lead hears the conference, never the whisper
    assert "Warm lead" not in caller_leg
    assert "<Say" not in caller_leg
    assert "<Conference" in caller_leg
    assert "callops-CA1" in caller_leg and "callops-CA1" in broker_leg


def test_the_word_transferred_is_never_claimed_without_a_broker_number(client, monkeypatch):
    from tests.callops_helpers import AUTH, payload_for

    monkeypatch.setattr(config, "BROKER_TRANSFER_NUMBER", None)
    response = client.post(
        "/v1/warm_transfer",
        json=payload_for(
            "warm_transfer",
            call_sid="CAharness0000000000000000000001",
            outcome="transferred",
            qualified_outcome="project_interested",
        ),
        headers=AUTH,
    )
    body = response.json()
    assert body["result"]["decision"] == "declined"
    steps = {step["step"]: step["status"] for step in body["result"]["transfer_steps"]}
    assert steps["dial_broker_leg"] == "skipped"
    assert steps["conference_bridge"] == "skipped"
    assert body["stored"]["outcome"] == "declined"


def test_with_a_broker_number_the_bridge_sequence_is_complete(client, monkeypatch):
    from tests.callops_helpers import AUTH, payload_for

    monkeypatch.setattr(config, "BROKER_TRANSFER_NUMBER", "+971509998888")
    response = client.post(
        "/v1/warm_transfer",
        json=payload_for(
            "warm_transfer",
            call_sid="CAharness0000000000000000000002",
            outcome="transferred",
            qualified_outcome="project_interested",
            broker_language="ar",
            broker_number="+971509998888",
        ),
        headers=AUTH,
    )
    body = response.json()["result"]
    assert body["decision"] == "transferred"
    steps = [step["step"] for step in body["transfer_steps"]]
    assert steps == [
        "collect_summary",
        "resolve_broker_number",
        "dial_broker_leg",
        "whisper_summary_to_broker",
        "conference_bridge",
        "return_outcome",
    ]
    assert body["whisper"]
    assert response.json()["stored"]["conference_name"].startswith("callops-")


def test_a_twilio_webhook_can_authenticate_by_signature(client, monkeypatch):
    """Twilio cannot present a bearer token; a valid signature is accepted."""
    import base64
    import hashlib
    import hmac

    from app.routers.voice_routes import twilio_signature_valid

    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "s3cret")
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "s3cret")
    url = "http://testserver/v1/voice/status-callback"
    params = _callbacks()["ringing"]
    material = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    signature = base64.b64encode(
        hmac.new(b"s3cret", material.encode(), hashlib.sha1).digest()
    ).decode()
    assert twilio_signature_valid(url, params, signature, "s3cret") is True
    assert twilio_signature_valid(url, params, "not-the-signature", "s3cret") is False
    forged = client.post(
        f"/v1/voice/status-callback?x=1",
        json=_callbacks()["ringing"],
        headers={"X-Twilio-Signature": signature},
    )
    assert forged.status_code == 401, "a signature for a different URL must not verify"


def test_a_webhook_tenant_comes_from_the_called_number_not_the_form():
    """A signature proves Twilio sent it; it does not name a brokerage."""
    from app.routers.voice_routes import tenant_for_number

    # an unmapped number belongs to the platform's own tenant, never to a name
    assert tenant_for_number("+10000000000") == os.environ.get("PLATFORM_TENANT", "local")
    os.environ["TENANT_PHONE_NUMBERS"] = "+971500000001:psi,+971500000002:other-brokerage"
    try:
        assert tenant_for_number("+971500000002") == "other-brokerage"
        assert tenant_for_number("971500000001") == "psi"
        assert tenant_for_number("+440000000000") == os.environ.get("PLATFORM_TENANT", "local")
    finally:
        os.environ.pop("TENANT_PHONE_NUMBERS", None)


def test_a_signed_webhook_cannot_name_a_tenant_in_the_form(client, monkeypatch):
    import base64
    import hashlib
    import hmac

    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "s3cret")
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "s3cret")
    url = "http://testserver/v1/voice/status-callback"  # the URL Twilio would sign
    params = {**_callbacks()["ringing"], "tenant_id": "somebody-else"}
    material = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    signature = base64.b64encode(
        hmac.new(b"s3cret", material.encode(), hashlib.sha1).digest()
    ).decode()
    signed = client.post("/v1/voice/status-callback", json=params, headers={"X-Twilio-Signature": signature})
    assert signed.status_code == 200
    assert signed.json()["tenant"]["tenant_id"] != "somebody-else"
    forged = client.post("/v1/voice/status-callback", json=params, headers={"X-Twilio-Signature": "nope"})
    assert forged.status_code == 401
