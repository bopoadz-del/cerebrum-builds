"""Connectors: one real outbound round trip, and honest stubs for the rest."""

from __future__ import annotations

import http.server
import json
import threading
from typing import Any, Dict, List

import pytest

from app import config, domain, security
from tests.callops_helpers import (  # noqa: F401 - client is a fixture
    AUTH, client, payload_for,
)


class _Receiver(http.server.BaseHTTPRequestHandler):
    received: List[Dict[str, Any]] = []

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler name
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8")
        type(self).received.append({"path": self.path, "body": raw, "headers": dict(self.headers)})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"received": true}')

    def log_message(self, *args: Any) -> None:  # keep the suite quiet
        return


@pytest.fixture()
def receiver():
    _Receiver.received = []
    server = http.server.HTTPServer(("127.0.0.1", 0), _Receiver)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}/callops"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_the_webhook_connector_makes_a_real_round_trip(client, receiver, monkeypatch):
    """One connector leaves the box: a real POST, a real 200 back."""
    monkeypatch.setattr(config, "EGRESS_ALLOWLIST", ("127.0.0.1",))
    monkeypatch.setattr(config, "BROKER_ALERT_WEBHOOK", receiver)
    response = client.post(
        "/v1/connectors/webhook/probe",
        json={"url": receiver},
        headers=AUTH,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["delivery"] == "delivered"
    assert body["response_code"] == 200
    assert _Receiver.received, "the probe reported delivery without a delivery"
    payload = json.loads(_Receiver.received[-1]["body"])
    assert payload["event"] == "callops.probe"


def test_a_qualified_lead_pings_the_sales_channel(client, receiver, monkeypatch):
    monkeypatch.setattr(config, "EGRESS_ALLOWLIST", ("127.0.0.1",))
    monkeypatch.setattr(config, "BROKER_ALERT_WEBHOOK", receiver)
    response = client.post(
        "/v1/notification",
        json=payload_for(
            "notification",
            trigger_event="lead_qualified",
            call_sid="CAlive000000000000000000000001",
            summary={"outcome": "project_interested", "collected": {"budget": 2000000}},
            body=None,
            target=receiver,
        ),
        headers=AUTH,
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["delivery"] == "delivered"
    assert response.json()["stored"]["response_code"] == 200
    delivered = json.loads(_Receiver.received[-1]["body"])
    assert delivered["trigger_event"] == "lead_qualified"
    assert "project_interested" in delivered["body"]


def test_the_webhook_connector_refuses_a_private_address():
    with pytest.raises(security.EgressRefused):
        security.check_egress("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(security.EgressRefused):
        security.check_egress("file:///etc/passwd")


def test_the_probe_refuses_a_private_url(client):
    response = client.post(
        "/v1/connectors/webhook/probe",
        json={"url": "http://10.0.0.5/hook"},
        headers=AUTH,
    )
    assert response.status_code == 422
    assert "private" in response.json()["detail"]


def test_notification_reports_a_stub_rather_than_a_delivery(client, monkeypatch):
    monkeypatch.setattr(config, "BROKER_ALERT_WEBHOOK", None)
    monkeypatch.setattr(config, "SALES_CHANNEL_WEBHOOK", None)
    response = client.post(
        "/v1/notification",
        json=payload_for("notification", trigger_event="lead_qualified", target=None),
        headers=AUTH,
    )
    body = response.json()
    assert body["result"]["delivery"] == "stubbed"
    assert "SALES_CHANNEL_WEBHOOK" in body["result"]["blocks_unavailable"]
    assert body["stored"]["unavailable_blocks"] == "SALES_CHANNEL_WEBHOOK"


def test_the_crm_destination_is_a_placeholder_that_claims_nothing(client, monkeypatch):
    monkeypatch.setattr(config, "CRM_DESTINATION", None)
    response = client.post(
        "/v1/crm_destination_placeholder",
        json=payload_for(
            "crm_destination_placeholder",
            call_sid="CAlive000000000000000000000002",
            outcome="project_interested",
            summary="",
            payload_shape="",
        ),
        headers=AUTH,
    )
    body = response.json()
    assert body["result"]["decision"] == "placeholder"
    assert body["result"]["blocks_unavailable"] == ["CRM_DESTINATION"]
    assert body["stored"]["destination_named"] in (False, 0)
    assert "payload_shape" in body["stored"]


def test_google_drive_builds_the_request_and_calls_nothing(client, monkeypatch):
    for name in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "GOOGLE_DRIVE_FOLDER_ID"):
        monkeypatch.setattr(config, name, None)
    response = client.post(
        "/v1/google_drive",
        json=payload_for("google_drive", operation="list"),
        headers=AUTH,
    )
    body = response.json()
    assert body["result"]["decision"] == "stubbed"
    assert body["result"]["blocks_unavailable"]
    assert body["result"]["would_call"].startswith("GET https://www.googleapis.com")
    assert body["stored"]["delivery"] == "stub"


def test_google_drive_runs_its_sequence_against_a_fake_transport(monkeypatch):
    from app.actions import google_drive

    for name, value in (
        ("GOOGLE_CLIENT_ID", "cid"),
        ("GOOGLE_CLIENT_SECRET", "sek"),
        ("GOOGLE_REFRESH_TOKEN", "ref"),
        ("GOOGLE_DRIVE_FOLDER_ID", "folder-1"),
    ):
        monkeypatch.setattr(config, name, value)
    monkeypatch.setenv("GOOGLE_ALLOW_API", "1")

    class FakeTransport:
        def __init__(self) -> None:
            self.calls: List[tuple] = []

        def post(self, url, payload, headers):
            self.calls.append(("post", url, payload))
            return {"access_token": "token-1"}

        def request(self, method, url, token, query=None):
            self.calls.append((method, url, token, query))
            return {"files": [{"id": "f1", "name": "az-zahra-price-list.xlsx"}]}

    transport = FakeTransport()
    outcome = google_drive.handle(
        payload_for("google_drive", operation="list"), transport=transport
    )
    assert outcome["decision"] == "live"
    assert outcome["performed"]["delivered"] is True
    assert [call[0] for call in transport.calls] == ["post", "GET"]
    assert transport.calls[0][1].endswith("/token")
    assert transport.calls[1][2] == "token-1"


def test_the_mcp_adapter_dispatches_a_capability_as_the_caller(client):
    listing = client.post(
        "/v1/mcp",
        json={"method": "tools/list", "params": {}},
        headers=AUTH,
    )
    assert listing.status_code == 200
    tools = listing.json()["jsonrpc"]["result"]["tools"]
    assert len(tools) == 12
    assert any(tool["name"] == "notification" for tool in tools)
    refusal = client.post(
        "/v1/mcp",
        json={"method": "tools/call", "params": {"name": "not_a_tool", "arguments": {}}},
        headers=AUTH,
    )
    assert refusal.status_code == 200
    assert refusal.json()["jsonrpc"]["error"]["code"] == -32601
    call = client.post(
        "/v1/mcp",
        json={
            "method": "tools/call",
            "params": {
                "name": "notification",
                "arguments": {"trigger_event": "call_failed", "call_sid": "CAmcp000000000000000000000001"},
            },
        },
        headers=AUTH,
    )
    assert call.status_code == 200
    assert call.json()["result"]["dispatched"] is True


def test_a_qualifying_lead_pings_the_channel_from_the_qualification_itself(client, receiver, monkeypatch):
    """The ping happens when the lead qualifies, not when someone remembers."""
    monkeypatch.setattr(config, "EGRESS_ALLOWLIST", ("127.0.0.1",))
    monkeypatch.setattr(config, "BROKER_ALERT_WEBHOOK", receiver)
    response = client.post(
        "/v1/qualification_and_broker_summary",
        json=payload_for(
            "qualification_and_broker_summary",
            call_sid="CAlive000000000000000000000003",
            outcome="project_interested",
            transcript="I like this project, budget around 2 million, handover in six months",
            project_tag="az-zahra",
        ),
        headers=AUTH,
    )
    assert response.status_code == 200, response.text
    alert = response.json()["result"]["notification"]
    assert alert["delivery"] == "delivered"
    assert alert["response_code"] == 200
    assert _Receiver.received, "no alert left the platform"
    delivered = json.loads(_Receiver.received[-1]["body"])
    assert delivered["trigger_event"] == "lead_qualified"
    assert "project_interested" in delivered["body"]


def test_a_not_interested_lead_does_not_ping_the_channel(client, receiver, monkeypatch):
    monkeypatch.setattr(config, "EGRESS_ALLOWLIST", ("127.0.0.1",))
    monkeypatch.setattr(config, "BROKER_ALERT_WEBHOOK", receiver)
    body = payload_for(
        "qualification_and_broker_summary",
        call_sid="CAlive000000000000000000000004",
        outcome="not_interested",
    )
    response = client.post("/v1/qualification_and_broker_summary", json=body, headers=AUTH)
    assert response.status_code == 200
    assert response.json()["result"]["notification"]["delivery"] == "not_required"
    assert _Receiver.received == []
