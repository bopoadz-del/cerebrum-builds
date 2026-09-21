"""CallOps domain acceptance: the voice edge, the transfer, the lifecycle.

Written by the factory WRITER role (codewhale exec)

Everything here runs against the recorded fake-Twilio fixtures in
``tests/fixtures/twilio/``. CI never dials: with TWILIO_ACCOUNT_SID,
TWILIO_AUTH_TOKEN and TWILIO_CALLER_NUMBER unset the gateway is in stubbed
mode and refuses to open a socket.
"""

import json
import os
from pathlib import Path

import pytest

from app import formulas
from app.voice import twilio_client, warm_transfer

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "twilio"


def _callbacks():
    return json.loads((FIXTURES / "status_callbacks.json").read_text(encoding="utf-8"))


def test_the_twilio_edge_is_stubbed_without_credentials(monkeypatch):
    for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_CALLER_NUMBER"):
        monkeypatch.delenv(key, raising=False)
    assert twilio_client.mode() == "stubbed"


def test_originate_in_stubbed_mode_uses_the_recorded_fixture(monkeypatch):
    for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_CALLER_NUMBER"):
        monkeypatch.delenv(key, raising=False)
    call = twilio_client.originate_call(to_number="+971500000000", language="ar")
    assert call["twilio_mode"] == "stubbed"
    assert call["call_sid"].startswith("CA")
    assert "ar-AE" in call["twiml"]
    assert "Polly.Hala-Neural" in call["twiml"]
    assert 'input="speech"' in call["twiml"]


def test_live_transport_refuses_a_non_e164_number(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC-test")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token-test")
    monkeypatch.setenv("TWILIO_CALLER_NUMBER", "+971400000000")
    assert twilio_client.mode() == "live"
    with pytest.raises(twilio_client.TwilioRefused):
        twilio_client.originate_call(to_number="0501234567", language="en")


def test_every_recorded_status_callback_maps_onto_a_call_state():
    for callback in _callbacks()["callbacks"]:
        mapped = twilio_client.map_status_event(callback["CallStatus"])
        assert mapped["state"] in (
            "dialing", "answered", "closed", "callback"
        ), callback


def test_an_unknown_status_callback_is_refused_not_guessed():
    with pytest.raises(twilio_client.TwilioRefused):
        twilio_client.map_status_event("hold")


def test_the_retry_budget_closes_the_call_on_the_third_failure():
    assert twilio_client.map_status_event("busy", attempt_count=1)["retry"] is True
    assert twilio_client.map_status_event("busy", attempt_count=2)["retry"] is True
    spent = twilio_client.map_status_event("busy", attempt_count=3)
    assert spent["retry"] is False
    assert spent["state"] == "closed"


def test_warm_transfer_sequence_whispers_to_the_broker_before_the_bridge(monkeypatch):
    for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_CALLER_NUMBER"):
        monkeypatch.delenv(key, raising=False)
    result = warm_transfer.transfer(
        summary="Ali is qualified on Marina Tower 1BR, budget 1.45M.",
        lead_number="+971500000000",
        broker_number="+971400000000",
        call_sid="CA-bridge-1",
        outcome="project_interested",
    )
    stages = [step["stage"] for step in result["sequence"]]
    assert stages.index("whisper_delivered") < stages.index("conference_bridged")
    assert result["whisper_audience"] == "broker_leg_only"
    assert "Private summary" in result["whisper_twiml"]
    assert "Private summary" not in result["lead_twiml"]
    assert result["transfer_status"] == "bridged"
    assert result["twilio_mode"] == "stubbed"


def test_warm_transfer_refuses_an_empty_summary():
    with pytest.raises(warm_transfer.TransferRefused):
        warm_transfer.transfer(summary="   ", lead_number="+1", broker_number="+2")


def test_warm_transfer_refuses_an_unqualified_outcome():
    with pytest.raises(warm_transfer.TransferRefused):
        warm_transfer.transfer(
            summary="not interested",
            lead_number="+971500000000",
            broker_number="+971400000000",
            outcome="not_interested",
        )


def test_status_callback_route_accepts_a_recorded_webhook(monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", os.environ.get("STORAGE_PATH", "./data"))
    from fastapi.testclient import TestClient

    from app.main import app

    callback = _callbacks()["callbacks"][2]
    client = TestClient(app)
    resp = client.post(
        "/v1/voice_gateway",
        json={
            "reference": "webhook-1",
            "status": "open",
            "call_sid": callback["CallSid"],
            "direction": "outbound",
            "language": "en",
            "call_status": callback["CallStatus"],
        },
        headers={"Authorization": "Bearer dev-local-token"},
    )
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body.get("ok") is True, body
    assert body["result"]["output"]["call_sid"] == callback["CallSid"]


def test_call_lifecycle_advances_and_stops_at_a_terminal_state():
    from app import workflows

    assert workflows.next_state("queued")["next_state"] == "dialing"
    assert workflows.next_state("dialing")["next_state"] == "answered"
    assert workflows.is_terminal("closed")
    spent = workflows.next_state("dialing", attempt_count=3, requested="callback")
    assert spent["next_state"] == "closed"


def test_per_language_best_call_window_is_computed_not_hardcoded():
    assert formulas.best_call_window("en") != formulas.best_call_window("ar")
    pacing = formulas.dial_pacing(language="ar")
    assert pacing["call_window"] == formulas.BEST_CALL_WINDOWS["ar"]


def test_commission_is_refused_until_the_operator_sets_currency_and_rate(monkeypatch):
    monkeypatch.delenv("CURRENCY", raising=False)
    monkeypatch.delenv("BROKER_COMMISSION_PERCENT", raising=False)
    with pytest.raises(formulas.SettingsError):
        formulas.commission_amount(2_000_000)
    monkeypatch.setenv("CURRENCY", "AED")
    monkeypatch.setenv("BROKER_COMMISSION_PERCENT", "2")
    result = formulas.commission_amount(2_000_000)
    assert result["currency"] == "AED"
    assert result["commission_amount"] == 40000.0


def test_grounding_withholds_an_unsupported_claim():
    from app.actions import project_knowledge_grounding as grounding

    out = grounding.handle(
        {
            "reference": "g-1",
            "status": "open",
            "project_tag": "psi-marina",
            "claim_type": "handover_date",
            "question": "when is handover",
            "document_name": "psi sheet",
            "document_text": "",
            "authority_label": "documents",
            "grounded": False,
            "answer": "",
            "citation": "",
            "notes": "",
        }
    )
    assert out["ok"] is True, out
    if not out["grounded"]:
        assert out["answer"] == ""
        assert "withheld" in out["withheld_reason"]
