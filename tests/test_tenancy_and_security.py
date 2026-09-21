"""Tenancy is resolved from the principal; the guards hold at the edge."""

from __future__ import annotations

import os

import pytest

from app import security, tenancy
from app.tenancy import TenantRefused, resolve_tenant
from tests.callops_helpers import (  # noqa: F401 - client is a fixture
    AUTH, OTHER_AUTH, TENANT, client, payload_for,
)


def test_no_token_is_refused_by_name():
    with pytest.raises(TenantRefused):
        resolve_tenant({})
    with pytest.raises(TenantRefused):
        resolve_tenant({"Authorization": "Bearer not-a-bound-token"})


def test_two_tokens_are_two_tenants():
    first = resolve_tenant({"Authorization": "Bearer dev-local-token"})
    second = resolve_tenant({"Authorization": "Bearer dev-local-token-b"})
    assert first.tenant_id != second.tenant_id


def test_a_payload_may_not_name_its_own_tenant(client):
    body = payload_for("notification")
    body["tenant_id"] = "somebody-else"
    response = client.post("/v1/notification", json=body, headers=AUTH)
    assert response.status_code == 422
    response = client.post("/v1/notification", json=body, headers=OTHER_AUTH)
    assert response.status_code == 422


def test_a_reserved_tenant_key_is_never_honoured():
    with pytest.raises(TenantRefused):
        tenancy.assert_no_payload_tenancy({"tenant": "x"})
    with pytest.raises(TenantRefused):
        security.reject_reserved({"tenant_id": "x"})
    with pytest.raises(TenantRefused):
        security.assert_no_payload_tenancy({"org_id": "x"})


def test_paths_cannot_escape_the_tenant_root(tmp_path):
    root = tmp_path / "drive"
    root.mkdir()
    assert security.safe_relative_path(str(root), "psi/sheet.csv")
    for bad in ("../secrets", "/etc/passwd", "a/../../b"):
        with pytest.raises(ValueError):
            security.safe_relative_path(str(root), bad)


def test_egress_is_denied_to_private_addresses():
    for url in ("http://127.0.0.1:8000/x", "http://10.1.2.3/x", "http://169.254.169.254/"):
        with pytest.raises(security.EgressRefused):
            security.check_egress(url)
    with pytest.raises(security.EgressRefused):
        security.check_egress("ftp://example.com/x")


def test_phones_and_secrets_are_masked_in_output():
    assert security.mask_phone("+971501234567").endswith("4567")
    assert security.mask_phone("+971501234567").startswith("*")
    redacted = security.redact({"api_key": "sk-live-123", "name": "Fatima"})
    assert redacted["api_key"] == "***redacted***"
    assert redacted["name"] == "Fatima"


def test_the_health_route_and_metrics_are_not_tenant_data(client):
    assert client.get("/health").status_code == 200
    assert client.get("/metrics").status_code == 200
    assert client.get("/").status_code == 200


def test_a_read_only_tenant_is_refused_on_a_write(client, monkeypatch):
    """Permissions have to be able to say no, or they are decoration."""
    monkeypatch.setenv(
        "TENANT_PERMISSIONS", f"{os.environ['PLATFORM_TENANT_B']}:read"
    )
    body = payload_for("notification", trigger_event="call_failed")
    refused = client.post("/v1/notification", json=body, headers=OTHER_AUTH)
    assert refused.status_code == 403
    assert "write" in refused.json()["detail"]
    allowed = client.get("/v1/notification", headers=OTHER_AUTH)
    assert allowed.status_code == 200
    monkeypatch.delenv("TENANT_PERMISSIONS", raising=False)


def test_mcp_calling_a_capability_needs_write_not_just_read(client, monkeypatch):
    monkeypatch.setenv("TENANT_PERMISSIONS", f"{os.environ['PLATFORM_TENANT_B']}:read")
    listing = client.post("/v1/mcp", json={"method": "tools/list", "params": {}}, headers=OTHER_AUTH)
    assert listing.status_code == 200
    calling = client.post(
        "/v1/mcp",
        json={"method": "tools/call", "params": {"name": "notification", "arguments": {"trigger_event": "call_failed"}}},
        headers=OTHER_AUTH,
    )
    assert calling.status_code == 403
    monkeypatch.delenv("TENANT_PERMISSIONS", raising=False)


def test_the_egress_guard_refuses_the_shared_address_space():
    with pytest.raises(security.EgressRefused):
        security.check_egress("http://100.100.100.100/hook")


def test_settings_reports_presence_and_never_a_value(client, monkeypatch):
    monkeypatch.setenv("CURRENCY", "AED")
    monkeypatch.setenv("VAT_RATE", "5%")
    response = client.get("/v1/settings", headers=AUTH)
    assert response.status_code == 200
    body = response.text
    assert "AED" not in body
    assert "5%" not in body
    money = response.json()["money"]
    assert money["CURRENCY"] is True and money["VAT_RATE"] is True
    assert money["BROKER_COMMISSION_RATE"] is False


def test_a_redirect_to_a_private_address_is_refused_not_followed(monkeypatch):
    """The egress guard judges every hop, not only the URL the caller sent.

    A public host that answers ``302 Location: http://169.254.169.254/...``
    must not be able to carry the platform onto the link-local network after
    the first URL passed. The guarded opener re-checks each hop and reports the
    refusal instead of delivering.
    """
    import http.server
    import threading

    from app import config, domain

    class _Redirector(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - http.server's spelling
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):  # silence the test log
            return

    server = http.server.HTTPServer(("127.0.0.1", 0), _Redirector)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(config, "EGRESS_ALLOWLIST", ("127.0.0.1",))
    try:
        outcome = domain.webhook_delivery(
            f"http://127.0.0.1:{server.server_port}/hook", {"event": "test"}, timeout=5
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert outcome["delivery"] == "refused", outcome
    assert "169.254.169.254" in str(outcome.get("error") or "")


def test_a_payload_may_not_name_its_own_tenant(client):
    """The edge refuses a payload that names a tenant, before any handler.

    This is the property the handlers rely on: because the route refuses the
    tenancy key outright, the only tenant a handler is ever handed over HTTP
    is the one the bearer token resolved.
    """
    body = payload_for("project_knowledge_grounding", tenant_id="somebody-else")
    response = client.post(
        "/v1/project_knowledge_grounding", json=body, headers=AUTH
    )
    assert response.status_code == 422, response.text
    assert "tenancy" in response.text


def test_a_handler_runs_as_the_tenant_it_was_handed_and_never_a_named_one(tmp_path, monkeypatch):
    """A direct in-process call uses the DEPLOYMENT's tenant, not the payload's.

    Two callers exist. The route hands a handler the tenant its token
    resolved; the platform's own runner (``app/domain_ops.py`` and the
    acceptance harness) calls ``handle()`` with no request at all, and that
    call runs as the tenant ``PLATFORM_TENANT`` declares -- a setting this
    deployment owns, not a name a caller supplied. The tenant a payload can
    never do is CHOOSE one: it is the deployment's, or it is the principal's.
    """
    monkeypatch.setenv("PLATFORM_TENANT", "psi")
    from app import tenancy
    from app.actions.local_drive import handle as local_drive_handle

    assert tenancy.deployment_tenant() == "psi"

    written = local_drive_handle(
        {
            "operation": "put",
            "relative_path": "leads.csv",
            "content": "name,phone\n",
            "reference": "no-principal",
            "status": "open",
        }
    )
    assert written["ok"] is True, written
    assert written["record"]["root"].endswith("psi")

    from_principal = local_drive_handle(
        {
            "operation": "put",
            "relative_path": "leads.csv",
            "content": "name,phone\n",
            "tenant_id": "other-brokerage",
            "reference": "principal",
            "status": "open",
        }
    )
    assert from_principal["ok"] is True, from_principal
    assert from_principal["record"]["root"].endswith("other-brokerage")
    assert from_principal["record"]["root"] != written["record"]["root"]


def test_the_mcp_surface_runs_a_tool_as_the_calling_tenant(client):
    """A second brokerage's MCP caller cannot read the first's corpus."""
    from app import retrieval

    first = "psi"
    retrieval.ingest(
        first,
        text="One bedroom apartments start from 1,250,000. Handover Q4 2027.",
        title="Az Zahra price list",
        project_tag="az-zahra",
        source="psi-price-list.pdf",
        certified=True,
    )
    assert retrieval.corpus_stats(first)["documents"]

    second = "other-brokerage"
    assert not retrieval.corpus_stats(second)["documents"]
    response = client.post(
        "/v1/mcp",
        json={
            "method": "tools/call",
            "params": {
                "name": "project_knowledge_grounding",
                "arguments": {
                    "project_tag": "az-zahra",
                    "question": "what is the starting price",
                    "claim_type": "price",
                    "reference": "mcp-tenant-test",
                    "status": "open",
                },
            },
        },
        headers=OTHER_AUTH,
    )
    assert response.status_code == 200, response.text
    text = str(response.json())
    assert "1,250,000" not in text, "the MCP call read another tenant's corpus"


def test_an_oversized_body_is_refused_by_its_declared_length(client):
    """The cap is enforced while the body arrives, not after buffering it."""
    from app.auth import MAX_BODY_BYTES

    payload = {"lead_name": "x" * 1024}
    payload["phone"] = "0" * (MAX_BODY_BYTES + 1024)
    response = client.post("/v1/lead_intake_and_dial_queue", json=payload, headers=AUTH)
    assert response.status_code == 422
    assert "too large" in response.json()["detail"]
