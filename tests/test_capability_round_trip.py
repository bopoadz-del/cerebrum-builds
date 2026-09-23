"""Every capability persists, reads back, and stays inside its tenant."""

from __future__ import annotations

import pytest

from app.models import CAPABILITY_IDS, MODELS
from tests.callops_helpers import (  # noqa: F401 - client is a fixture
    AUTH, OTHER_AUTH, client, payload_for,
)

CAPS = list(CAPABILITY_IDS)

#: Realistic inputs per capability, plus the columns that must come back
#: exactly as sent. A handler owns its derived columns (dialable, answer,
#: decision, hashes …); the inputs the operator supplied are the contract,
#: and those are what a round trip has to preserve.
INPUTS = {
    "lead_intake_and_dial_queue": (
        {"lead_name": "Fatima Al Ali", "phone": "+971501234567", "project_tag": "az-zahra",
         "language": "ar", "campaign": "psi-q3", "source_file": "leads.csv"},
        ["lead_name", "phone", "project_tag", "language", "campaign", "source_file", "reference", "status"],
    ),
    "call_state_machine": (
        {"call_sid": "CArt00000000000000000000000001", "event": "dial", "previous_state": "queued",
         "source": "voice_gateway", "lead_id": "17"},
        ["call_sid", "event", "previous_state", "source", "lead_id", "reference", "status"],
    ),
    "project_knowledge_grounding": (
        {"project_tag": "az-zahra", "question": "what is the starting price", "claim_type": "price",
         "campaign": "psi-q3"},
        ["project_tag", "question", "claim_type", "campaign", "reference", "status"],
    ),
    "voice_gateway": (
        {"call_sid": "CArt00000000000000000000000002", "to_number": "+971501234567",
         "voice_action": "originate", "language": "ar"},
        ["call_sid", "to_number", "voice_action", "language", "reference", "status"],
    ),
    "warm_transfer": (
        {"call_sid": "CArt00000000000000000000000003", "outcome": "transferred",
         "qualified_outcome": "project_interested", "project_tag": "az-zahra", "lead_id": "17",
         "broker_number": "+971509998888"},
        ["call_sid", "outcome", "qualified_outcome", "project_tag", "lead_id", "reference", "status"],
    ),
    "qualification_and_broker_summary": (
        {"call_sid": "CArt00000000000000000000000004", "outcome": "project_interested",
         "language": "ar", "project_tag": "az-zahra", "lead_name": "Fatima Al Ali",
         "property_type": "apartment", "budget": 2000000.0, "area": "Dubai Marina", "timeline": "six_months"},
        ["call_sid", "outcome", "language", "project_tag", "lead_name", "property_type", "budget",
         "area", "timeline", "reference", "status"],
    ),
    "outcome_capture_and_ledger": (
        {"call_sid": "CArt00000000000000000000000005", "event_type": "answered",
         "outcome": "project_interested", "actor": "operator", "campaign": "psi-q3"},
        ["call_sid", "event_type", "outcome", "actor", "campaign", "reference", "status"],
    ),
    "crm_destination_placeholder": (
        {"call_sid": "CArt00000000000000000000000006", "outcome": "project_interested",
         "intended_method": "POST"},
        ["call_sid", "outcome", "intended_method", "reference", "status"],
    ),
    "notification": (
        {"trigger_event": "lead_qualified", "channel": "webhook", "target": "https://hooks.example.test/x",
         "subject": "Warm lead", "body": "Fatima is interested", "call_sid": "CArt00000000000000000000000007"},
        ["trigger_event", "channel", "target", "subject", "body", "call_sid", "reference", "status"],
    ),
    "local_drive": (
        {"operation": "put", "relative_path": "psi/az-zahra.csv", "content": "name,phone\nFatima,+971501234567\n"},
        ["operation", "relative_path", "content", "reference", "status"],
    ),
    "google_drive": (
        {"operation": "list", "folder_id": "folder-1", "file_name": "az-zahra.xlsx",
         "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        ["operation", "folder_id", "file_name", "mime_type", "reference", "status"],
    ),
    "mcp_adapter": (
        {"method": "tools/list", "catalog_scope": "platform"},
        ["method", "catalog_scope", "reference", "status"],
    ),
}


def body_and_echo(capability: str):
    overrides, echo = INPUTS[capability]
    return payload_for(capability, **overrides), echo


def test_the_roster_is_the_twelve_factory_capabilities():
    assert len(CAPS) == 12
    for required in (
        "lead_intake_and_dial_queue",
        "call_state_machine",
        "project_knowledge_grounding",
        "voice_gateway",
        "warm_transfer",
        "qualification_and_broker_summary",
        "outcome_capture_and_ledger",
        "crm_destination_placeholder",
        "notification",
        "local_drive",
        "google_drive",
        "mcp_adapter",
    ):
        assert required in CAPS


@pytest.mark.parametrize("capability", CAPS)
def test_a_valid_record_persists_and_reads_back(client, capability):
    body, echo = body_and_echo(capability)
    created = client.post(f"/v1/{capability}", json=body, headers=AUTH)
    assert created.status_code == 200, created.text
    payload = created.json()
    assert payload["ok"] is True
    record = payload["stored"]
    assert record["id"] is not None
    assert payload["authority"]["precedence"] == "precedence.v1"

    fetched = client.get(f"/v1/{capability}/{record['id']}", headers=AUTH)
    assert fetched.status_code == 200
    stored = fetched.json()["stored"]
    assert stored["id"] == record["id"]
    for key in echo:
        assert stored[key] == body[key], (capability, key, stored[key], body[key])
    for key in body:
        assert key in stored, (capability, key)


@pytest.mark.parametrize("capability", CAPS)
def test_another_tenant_cannot_read_the_record(client, capability):
    body, _echo = body_and_echo(capability)
    created = client.post(f"/v1/{capability}", json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    response = client.get(f"/v1/{capability}/{record_id}", headers=OTHER_AUTH)
    assert response.status_code == 404, "cross-tenant read must be 404, not 403 and never the row"


@pytest.mark.parametrize("capability", CAPS)
def test_listing_only_returns_the_callers_rows(client, capability):
    body, _echo = body_and_echo(capability)
    client.post(f"/v1/{capability}", json=body, headers=AUTH)
    mine = client.get(f"/v1/{capability}", headers=AUTH)
    theirs = client.get(f"/v1/{capability}", headers=OTHER_AUTH)
    assert mine.status_code == 200 and theirs.status_code == 200
    assert len(mine.json()["items"]) >= 1
    for row in theirs.json()["items"]:
        assert row["id"] not in {item["id"] for item in mine.json()["items"]}


def test_unknown_capability_is_a_404(client):
    assert client.post("/v1/not_a_capability", json={"reference": "r"}, headers=AUTH).status_code == 404


def test_update_and_delete_are_tenant_scoped(client):
    first = payload_for("notification", trigger_event="call_failed", subject="first", reference="upd-1")
    second = payload_for("notification", trigger_event="call_failed", subject="second", reference="upd-2")
    created = client.post("/v1/notification", json=first, headers=AUTH)
    record_id = created.json()["stored"]["id"]
    updated = client.put(f"/v1/notification/{record_id}", json=second, headers=AUTH)
    assert updated.status_code == 200
    assert updated.json()["stored"]["subject"] == "second"
    assert client.put(
        f"/v1/notification/{record_id}",
        json=payload_for("notification", trigger_event="call_failed", subject="third"),
        headers=OTHER_AUTH,
    ).status_code == 404
    assert client.delete(f"/v1/notification/{record_id}", headers=AUTH).status_code == 200
    assert client.get(f"/v1/notification/{record_id}", headers=AUTH).status_code == 404


def test_declared_columns_are_the_models_fields():
    for capability in CAPS:
        assert MODELS[capability].FIELDS
        assert MODELS[capability].ENTITY == capability
        assert "reference" in MODELS[capability].FIELDS
        assert "status" in MODELS[capability].FIELDS


def test_each_handlers_vocabulary_is_the_one_its_contract_declares():
    """A handler may not enforce a vocabulary its own model does not declare.

    The route validates from the model, the handler validates from its own
    list: if those two disagree, one of them is wrong and the operator finds
    out at the worst moment.
    """
    import importlib

    for capability in CAPS:
        module = importlib.import_module(f"app.actions.{capability}")
        model = MODELS[capability]
        for name, values in getattr(module, "ALLOWED", {}).items():
            declared = model.ALLOWED_VALUES.get(name)
            assert declared is not None, (capability, name)
            assert list(declared) == list(values), (capability, name, list(declared), list(values))
        for name in getattr(module, "REQUIRED_FIELDS", []):
            assert name in model.REQUIRED, (capability, name)
        assert module.CAPABILITY_ID == capability
        assert "Written by the factory WRITER role (codewhale exec)" in (module.__doc__ or "")


@pytest.mark.parametrize("capability", CAPS)
def test_a_record_that_does_not_exist_is_404_not_403(client, capability):
    """An id nobody holds is absent, never "forbidden".

    403 would confirm the row exists for someone else; 404 says the caller's
    tenant has no such record, which is the whole point of tenant-scoped
    reads. This is asserted for an id that was never written, not only for
    one just deleted.
    """
    response = client.get(f"/v1/{capability}/999999", headers=AUTH)
    assert response.status_code == 404, response.text
    body = response.json()
    assert "999999" not in str(body)
