"""One counter-case block per capability: what CallOps refuses, by name.

Each block asks the four questions the floor names — a payload with a
required field missing, a value outside a declared vocabulary, another
tenant's record, and a malformed body — plus the two the platform adds on
its own authority: an unauthenticated write, and a write that tries to name
its own tenant.
"""

from __future__ import annotations

import pytest

from tests.callops_helpers import (  # noqa: F401 - client is a fixture
    AUTH, OTHER_AUTH, client, payload_for,
)


def _sample(capability: str) -> dict:
    return payload_for(capability)


def _required(capability: str) -> str:
    return list(MODELS[capability].REQUIRED)[0]


def _vocabulary(capability: str) -> str:
    return list(MODELS[capability].ALLOWED_VALUES)[0]


from app.models import MODELS  # noqa: E402  (used by the helpers above)



def test_lead_intake_and_dial_queue_counter_cases(client):
    """Lead intake & dial queue: what it refuses."""
    route = "/v1/lead_intake_and_dial_queue"
    body = _sample('lead_intake_and_dial_queue')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'lead_name'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'language': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_call_state_machine_counter_cases(client):
    """Call state machine: what it refuses."""
    route = "/v1/call_state_machine"
    body = _sample('call_state_machine')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'call_sid'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'event': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_project_knowledge_grounding_counter_cases(client):
    """Project knowledge grounding: what it refuses."""
    route = "/v1/project_knowledge_grounding"
    body = _sample('project_knowledge_grounding')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'project_tag'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'claim_type': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_voice_gateway_counter_cases(client):
    """Voice gateway (Twilio edge): what it refuses."""
    route = "/v1/voice_gateway"
    body = _sample('voice_gateway')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'call_sid'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    # 'action' is a reserved word and is never a domain field here, so the
    # vocabulary probe names the column the voice edge actually declares.
    bad = {**body, 'voice_action': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_warm_transfer_counter_cases(client):
    """Warm transfer: what it refuses."""
    route = "/v1/warm_transfer"
    body = _sample('warm_transfer')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'call_sid'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'outcome': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_qualification_and_broker_summary_counter_cases(client):
    """Qualification & broker summary: what it refuses."""
    route = "/v1/qualification_and_broker_summary"
    body = _sample('qualification_and_broker_summary')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'call_sid'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'outcome': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_outcome_capture_and_ledger_counter_cases(client):
    """Outcome capture & ledger: what it refuses."""
    route = "/v1/outcome_capture_and_ledger"
    body = _sample('outcome_capture_and_ledger')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'call_sid'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'event_type': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_crm_destination_placeholder_counter_cases(client):
    """CRM destination placeholder: what it refuses."""
    route = "/v1/crm_destination_placeholder"
    body = _sample('crm_destination_placeholder')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'call_sid'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'delivery': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_notification_counter_cases(client):
    """Notification: what it refuses."""
    route = "/v1/notification"
    body = _sample('notification')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'trigger_event'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'trigger_event': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_local_drive_counter_cases(client):
    """Local drive: what it refuses."""
    route = "/v1/local_drive"
    body = _sample('local_drive')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'operation'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'operation': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_google_drive_counter_cases(client):
    """Google Drive: what it refuses."""
    route = "/v1/google_drive"
    body = _sample('google_drive')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'operation'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'operation': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404


def test_mcp_adapter_counter_cases(client):
    """MCP adapter: what it refuses."""
    route = "/v1/mcp_adapter"
    body = _sample('mcp_adapter')
    # nothing at all is not a record, and an anonymous caller is not a tenant
    assert client.post(route, json={}).status_code == 401
    assert client.post(route, json={}, headers=AUTH).status_code == 422
    # a partial record is refused, never completed by the server
    partial = {k: v for k, v in body.items() if k != 'method'}
    assert client.post(route, json=partial, headers=AUTH).status_code == 422
    # the payload may not name its own tenant
    named = {**body, "tenant_id": "somebody-else"}
    assert client.post(route, json=named, headers=AUTH).status_code == 422
    # garbage in is a refusal, never a 500 and never a stored row
    assert client.post(route, json=[], headers=AUTH).status_code == 422
    # a column that accepts any string is not that column
    bad = {**body, 'method': "__not_in_contract__"}
    assert client.post(route, json=bad, headers=AUTH).status_code == 422
    # another tenant's row does not exist for this caller
    created = client.post(route, json=body, headers=AUTH)
    assert created.status_code == 200
    record_id = created.json()["stored"]["id"]
    assert client.get(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
    assert client.delete(f"{route}/{record_id}", headers=OTHER_AUTH).status_code == 404
