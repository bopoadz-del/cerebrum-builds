"""The HTTP surface answers, and what it answers has the right shape."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {'Authorization': 'Bearer ' + __import__('os').environ.get('PLATFORM_TOKEN', 'dev-local-token')}


def _listed(payload):
    """Same list shapes as PRODUCT round-trip (_listed / _listed_records).

    Hard-coding listed.json()['items'] KeyError'd when GET answered
    {ok: False} or {records: [...]} — pytest then reported only
    'suite is red' with no capability id (sess_5dfb4a3 class).
    """
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    if payload.get("ok") is False:
        return []
    for key in ("items", "records", "results", "data", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["ok"] is True
    names = {item["name"] for item in body["checks"]}
    assert {"process", "persistent_disk", "database", "migrations"} <= names
    assert all(item["ok"] for item in body["checks"])


def test_kernel_jobs_roster():
    """GET /v1/jobs publishes every kernel JD; distinctive routes answer."""
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    by_kernel = {j["kernel"]: j for j in jobs}
    assert set(by_kernel) == {
        "COLLECTOR", "CLONER", "WRITER", "TESTER", "STORE_MANAGER"
    }
    assert by_kernel["COLLECTOR"]["title"] == "Binding surveyor"
    assert by_kernel["CLONER"]["title"] == "Block stocker"
    assert by_kernel["WRITER"]["title"] == "Platform manufacturer"
    assert by_kernel["TESTER"]["title"] == "Acceptance inspector"
    assert by_kernel["STORE_MANAGER"]["title"] == "Store registrar"
    for job in jobs:
        assert job["mandate"] and job["http_routes"] and job["agent"]
    catalog = client.get("/v1/catalog")
    assert catalog.status_code == 200
    assert catalog.json()["kernel"] == "COLLECTOR"
    inventory = client.get("/v1/inventory")
    assert inventory.status_code == 200
    assert inventory.json()["kernel"] == "CLONER"
    assert "lock" in inventory.json()
    caps_resp = client.get("/v1/capabilities")
    assert caps_resp.status_code == 200
    assert isinstance(caps_resp.json()["items"], list)
    gates = client.get("/v1/gates")
    assert gates.status_code == 200
    assert gates.json()["kernel"] == "TESTER"
    assert gates.json()["runs_over_http"] is False
    prov = client.get("/v1/provenance")
    assert prov.status_code == 200
    assert prov.json()["kernel"] == "STORE_MANAGER"


def test_every_capability_route_answers():
    """Code-phase: each capability POST answers HTTP 200 JSON.
    Store ok: False is allowed here — acceptance is the pilot test."""
    failures = []
    payload = {'reference': 'sample', 'status': 'open', 'property_name': 'sample', 'building': 'sample', 'floor': 1, 'room_number': 'sample', 'room_type': 'standard', 'capacity': 1, 'room_status': 'available', 'notes': 'sample'}
    resp = client.post("/v1/property_and_room_registry", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('property_and_room_registry: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('property_and_room_registry: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('property_and_room_registry: JSON body is not a dict')
            listed = client.get("/v1/property_and_room_registry", headers=AUTH)
            if listed.status_code != 200:
                failures.append('property_and_room_registry list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'room_number': 'sample', 'arrival_date': '2026-09-03', 'departure_date': '2026-09-03', 'guests_count': 1, 'stay_status': 'reserved', 'folio_currency': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/front_desk_and_guest_stay", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('front_desk_and_guest_stay: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('front_desk_and_guest_stay: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('front_desk_and_guest_stay: JSON body is not a dict')
            listed = client.get("/v1/front_desk_and_guest_stay", headers=AUTH)
            if listed.status_code != 200:
                failures.append('front_desk_and_guest_stay list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'work_type': 'housekeeping', 'room_number': 'sample', 'priority': 'low', 'due_date': '2026-09-03', 'assigned_to': 'sample', 'work_status': 'open', 'notes': 'sample'}
    resp = client.post("/v1/housekeeping_and_maintenance", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('housekeeping_and_maintenance: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('housekeeping_and_maintenance: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('housekeeping_and_maintenance: JSON body is not a dict')
            listed = client.get("/v1/housekeeping_and_maintenance", headers=AUTH)
            if listed.status_code != 200:
                failures.append('housekeeping_and_maintenance list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'recency_days': 1, 'frequency': 1, 'monetary': 1, 'segment': 'champion', 'delivery_channel': 'mcp', 'offer_code': 'id-1', 'notes': 'sample'}
    resp = client.post("/v1/guest_engagement_and_segmentation", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('guest_engagement_and_segmentation: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('guest_engagement_and_segmentation: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('guest_engagement_and_segmentation: JSON body is not a dict')
            listed = client.get("/v1/guest_engagement_and_segmentation", headers=AUTH)
            if listed.status_code != 200:
                failures.append('guest_engagement_and_segmentation list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'document_kind': 'manual', 'question': 'sample', 'document_text': 'sample', 'attachment_path': 'sample', 'answer': 'sample', 'source_document': 'sample', 'authority_label': 'certified', 'notes': 'sample'}
    resp = client.post("/v1/document_and_knowledge_answers", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_and_knowledge_answers: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('document_and_knowledge_answers: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('document_and_knowledge_answers: JSON body is not a dict')
            listed = client.get("/v1/document_and_knowledge_answers", headers=AUTH)
            if listed.status_code != 200:
                failures.append('document_and_knowledge_answers list: HTTP ' + str(listed.status_code))

    payload = {'setting': 'sample', 'reference': 'sample', 'status': 'open', 'folio_reference': 'sample', 'charge_type': 'room', 'amount': 1, 'currency': 'sample', 'tax_rate_percent': 1, 'total_amount': 1, 'notes': 'sample'}
    resp = client.post("/v1/operations_billing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('operations_billing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('operations_billing: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('operations_billing: JSON body is not a dict')
            listed = client.get("/v1/operations_billing", headers=AUTH)
            if listed.status_code != 200:
                failures.append('operations_billing list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'dashboard_name': 'sample', 'widget': 'occupancy', 'window_days': 1, 'operator_role': 'operator', 'occupancy_percent': 1, 'open_work_orders': 1, 'notes': 'sample'}
    resp = client.post("/v1/operations_oversight_dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('operations_oversight_dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('operations_oversight_dashboard: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('operations_oversight_dashboard: JSON body is not a dict')
            listed = client.get("/v1/operations_oversight_dashboard", headers=AUTH)
            if listed.status_code != 200:
                failures.append('operations_oversight_dashboard list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'system': 'opera', 'resource': 'sample', 'direction': 'inbound', 'payload_format': 'json', 'endpoint_url': 'sample', 'records_seen': 1, 'notes': 'sample'}
    resp = client.post("/v1/external_integration_adapter", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('external_integration_adapter: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('external_integration_adapter: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('external_integration_adapter: JSON body is not a dict')
            listed = client.get("/v1/external_integration_adapter", headers=AUTH)
            if listed.status_code != 200:
                failures.append('external_integration_adapter list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'reference': 'sample', 'status': 'open', 'property_name': 'sample', 'building': 'sample', 'floor': 1, 'room_number': 'sample', 'room_type': 'standard', 'capacity': 1, 'room_status': 'available', 'notes': 'sample'}
    resp = client.post("/v1/property_and_room_registry", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('property_and_room_registry: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('property_and_room_registry rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/property_and_room_registry", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('property_and_room_registry list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('property_and_room_registry list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('property_and_room_registry accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/property_and_room_registry/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('property_and_room_registry get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/property_and_room_registry/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('property_and_room_registry missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'room_number': 'sample', 'arrival_date': '2026-09-03', 'departure_date': '2026-09-03', 'guests_count': 1, 'stay_status': 'reserved', 'folio_currency': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/front_desk_and_guest_stay", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('front_desk_and_guest_stay: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('front_desk_and_guest_stay rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/front_desk_and_guest_stay", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('front_desk_and_guest_stay list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('front_desk_and_guest_stay list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('front_desk_and_guest_stay accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/front_desk_and_guest_stay/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('front_desk_and_guest_stay get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/front_desk_and_guest_stay/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('front_desk_and_guest_stay missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'work_type': 'housekeeping', 'room_number': 'sample', 'priority': 'low', 'due_date': '2026-09-03', 'assigned_to': 'sample', 'work_status': 'open', 'notes': 'sample'}
    resp = client.post("/v1/housekeeping_and_maintenance", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('housekeeping_and_maintenance: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('housekeeping_and_maintenance rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/housekeeping_and_maintenance", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('housekeeping_and_maintenance list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('housekeeping_and_maintenance list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('housekeeping_and_maintenance accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/housekeeping_and_maintenance/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('housekeeping_and_maintenance get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/housekeeping_and_maintenance/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('housekeeping_and_maintenance missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'recency_days': 1, 'frequency': 1, 'monetary': 1, 'segment': 'champion', 'delivery_channel': 'mcp', 'offer_code': 'id-1', 'notes': 'sample'}
    resp = client.post("/v1/guest_engagement_and_segmentation", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('guest_engagement_and_segmentation: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('guest_engagement_and_segmentation rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/guest_engagement_and_segmentation", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('guest_engagement_and_segmentation list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('guest_engagement_and_segmentation list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('guest_engagement_and_segmentation accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/guest_engagement_and_segmentation/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('guest_engagement_and_segmentation get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/guest_engagement_and_segmentation/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('guest_engagement_and_segmentation missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'document_kind': 'manual', 'question': 'sample', 'document_text': 'sample', 'attachment_path': 'sample', 'answer': 'sample', 'source_document': 'sample', 'authority_label': 'certified', 'notes': 'sample'}
    resp = client.post("/v1/document_and_knowledge_answers", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_and_knowledge_answers: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('document_and_knowledge_answers rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/document_and_knowledge_answers", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('document_and_knowledge_answers list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('document_and_knowledge_answers list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('document_and_knowledge_answers accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/document_and_knowledge_answers/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('document_and_knowledge_answers get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/document_and_knowledge_answers/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('document_and_knowledge_answers missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'setting': 'sample', 'reference': 'sample', 'status': 'open', 'folio_reference': 'sample', 'charge_type': 'room', 'amount': 1, 'currency': 'sample', 'tax_rate_percent': 1, 'total_amount': 1, 'notes': 'sample'}
    resp = client.post("/v1/operations_billing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('operations_billing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('operations_billing rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/operations_billing", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('operations_billing list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('operations_billing list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('operations_billing accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/operations_billing/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('operations_billing get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/operations_billing/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('operations_billing missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'status': 'open', 'dashboard_name': 'sample', 'widget': 'occupancy', 'window_days': 1, 'operator_role': 'operator', 'occupancy_percent': 1, 'open_work_orders': 1, 'notes': 'sample'}
    resp = client.post("/v1/operations_oversight_dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('operations_oversight_dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('operations_oversight_dashboard rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/operations_oversight_dashboard", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('operations_oversight_dashboard list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('operations_oversight_dashboard list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('operations_oversight_dashboard accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/operations_oversight_dashboard/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('operations_oversight_dashboard get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/operations_oversight_dashboard/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('operations_oversight_dashboard missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'status': 'open', 'system': 'opera', 'resource': 'sample', 'direction': 'inbound', 'payload_format': 'json', 'endpoint_url': 'sample', 'records_seen': 1, 'notes': 'sample'}
    resp = client.post("/v1/external_integration_adapter", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('external_integration_adapter: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('external_integration_adapter rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/external_integration_adapter", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('external_integration_adapter list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('external_integration_adapter list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('external_integration_adapter accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/external_integration_adapter/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('external_integration_adapter get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/external_integration_adapter/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('external_integration_adapter missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
