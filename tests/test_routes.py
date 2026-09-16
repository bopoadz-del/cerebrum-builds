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
    payload = {'owner_name': 'sample', 'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'species': 'sample', 'breed': 'sample', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'date_of_birth': 'sample', 'weight_kg': 'sample', 'vaccination_status': 'open', 'allergies': 'sample', 'clinical_notes': 'sample'}
    resp = client.post("/v1/patient_records", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('patient_records: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('patient_records: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('patient_records: JSON body is not a dict')
            listed = client.get("/v1/patient_records")
            if listed.status_code != 200:
                failures.append('patient_records list: HTTP ' + str(listed.status_code))

    payload = {'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'owner_name': 'sample', 'appointment_date': '2026-09-03', 'appointment_time': '10:00:00', 'duration_minutes': 'sample', 'visit_reason': 'sample', 'room': 'sample', 'appointment_status': 'open'}
    resp = client.post("/v1/appointment_scheduling", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('appointment_scheduling: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('appointment_scheduling: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('appointment_scheduling: JSON body is not a dict')
            listed = client.get("/v1/appointment_scheduling")
            if listed.status_code != 200:
                failures.append('appointment_scheduling list: HTTP ' + str(listed.status_code))

    payload = {'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'treatment_type': 'sample', 'diagnosis': 'sample', 'procedure_notes': 'sample', 'medication': 'sample', 'dosage': 'sample', 'treatment_date': '2026-09-03', 'follow_up_date': '2026-09-03', 'attachment_path': 'sample'}
    resp = client.post("/v1/treatment_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('treatment_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('treatment_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('treatment_management: JSON body is not a dict')
            listed = client.get("/v1/treatment_management")
            if listed.status_code != 200:
                failures.append('treatment_management list: HTTP ' + str(listed.status_code))

    payload = {'client_name': 'sample', 'invoice_number': 'sample', 'reference': 'sample', 'status': 'open', 'pet_name': 'sample', 'line_items': 'sample', 'subtotal': 'sample', 'tax_rate': 'sample', 'total_amount': 'sample', 'payment_status': 'open', 'payment_method': 'sample', 'invoice_date': '2026-09-03', 'attachment_path': 'sample'}
    resp = client.post("/v1/billing_invoicing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('billing_invoicing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('billing_invoicing: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('billing_invoicing: JSON body is not a dict')
            listed = client.get("/v1/billing_invoicing")
            if listed.status_code != 200:
                failures.append('billing_invoicing list: HTTP ' + str(listed.status_code))

    payload = {'item_name': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'category': 'sample', 'quantity': 1, 'reorder_level': 'sample', 'unit_cost': 'sample', 'supplier': 'sample', 'expiry_date': '2026-09-03'}
    resp = client.post("/v1/inventory_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('inventory_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('inventory_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('inventory_management: JSON body is not a dict')
            listed = client.get("/v1/inventory_management")
            if listed.status_code != 200:
                failures.append('inventory_management list: HTTP ' + str(listed.status_code))

    payload = {'actor': 'sample', 'event_type': 'sample', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_id': 'id-1', 'actor_role': 'sample', 'action_taken': 'sample', 'details': 'sample', 'occurred_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/audit_trail", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit_trail: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('audit_trail: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('audit_trail: JSON body is not a dict')
            listed = client.get("/v1/audit_trail")
            if listed.status_code != 200:
                failures.append('audit_trail list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'role_name': 'sample', 'status': 'open', 'display_name': 'sample', 'permissions': 'sample', 'access_level': 'sample', 'department': 'sample', 'is_active': True}
    resp = client.post("/v1/role_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('role_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('role_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('role_management: JSON body is not a dict')
            listed = client.get("/v1/role_management")
            if listed.status_code != 200:
                failures.append('role_management list: HTTP ' + str(listed.status_code))

    payload = {'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'dimension': 'sample'}
    resp = client.post("/v1/clinic_analytics", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('clinic_analytics: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('clinic_analytics: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('clinic_analytics: JSON body is not a dict')
            listed = client.get("/v1/clinic_analytics")
            if listed.status_code != 200:
                failures.append('clinic_analytics list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'owner_name': 'sample', 'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'species': 'sample', 'breed': 'sample', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'date_of_birth': 'sample', 'weight_kg': 'sample', 'vaccination_status': 'open', 'allergies': 'sample', 'clinical_notes': 'sample'}
    resp = client.post("/v1/patient_records", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('patient_records: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('patient_records rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/patient_records")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('patient_records list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('patient_records list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('patient_records accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/patient_records/{item_id}")
                if got.status_code != 200:
                    failures.append('patient_records get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/patient_records/999999")
                if missing.status_code != 404:
                    failures.append('patient_records missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'owner_name': 'sample', 'appointment_date': '2026-09-03', 'appointment_time': '10:00:00', 'duration_minutes': 'sample', 'visit_reason': 'sample', 'room': 'sample', 'appointment_status': 'open'}
    resp = client.post("/v1/appointment_scheduling", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('appointment_scheduling: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('appointment_scheduling rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/appointment_scheduling")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('appointment_scheduling list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('appointment_scheduling list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('appointment_scheduling accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/appointment_scheduling/{item_id}")
                if got.status_code != 200:
                    failures.append('appointment_scheduling get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/appointment_scheduling/999999")
                if missing.status_code != 404:
                    failures.append('appointment_scheduling missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'treatment_type': 'sample', 'diagnosis': 'sample', 'procedure_notes': 'sample', 'medication': 'sample', 'dosage': 'sample', 'treatment_date': '2026-09-03', 'follow_up_date': '2026-09-03', 'attachment_path': 'sample'}
    resp = client.post("/v1/treatment_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('treatment_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('treatment_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/treatment_management")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('treatment_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('treatment_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('treatment_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/treatment_management/{item_id}")
                if got.status_code != 200:
                    failures.append('treatment_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/treatment_management/999999")
                if missing.status_code != 404:
                    failures.append('treatment_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'client_name': 'sample', 'invoice_number': 'sample', 'reference': 'sample', 'status': 'open', 'pet_name': 'sample', 'line_items': 'sample', 'subtotal': 'sample', 'tax_rate': 'sample', 'total_amount': 'sample', 'payment_status': 'open', 'payment_method': 'sample', 'invoice_date': '2026-09-03', 'attachment_path': 'sample'}
    resp = client.post("/v1/billing_invoicing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('billing_invoicing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('billing_invoicing rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/billing_invoicing")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('billing_invoicing list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('billing_invoicing list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('billing_invoicing accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/billing_invoicing/{item_id}")
                if got.status_code != 200:
                    failures.append('billing_invoicing get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/billing_invoicing/999999")
                if missing.status_code != 404:
                    failures.append('billing_invoicing missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'item_name': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'category': 'sample', 'quantity': 1, 'reorder_level': 'sample', 'unit_cost': 'sample', 'supplier': 'sample', 'expiry_date': '2026-09-03'}
    resp = client.post("/v1/inventory_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('inventory_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('inventory_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/inventory_management")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('inventory_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('inventory_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('inventory_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/inventory_management/{item_id}")
                if got.status_code != 200:
                    failures.append('inventory_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/inventory_management/999999")
                if missing.status_code != 404:
                    failures.append('inventory_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'actor': 'sample', 'event_type': 'sample', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_id': 'id-1', 'actor_role': 'sample', 'action_taken': 'sample', 'details': 'sample', 'occurred_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/audit_trail", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit_trail: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('audit_trail rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/audit_trail")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('audit_trail list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('audit_trail list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('audit_trail accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/audit_trail/{item_id}")
                if got.status_code != 200:
                    failures.append('audit_trail get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/audit_trail/999999")
                if missing.status_code != 404:
                    failures.append('audit_trail missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'role_name': 'sample', 'status': 'open', 'display_name': 'sample', 'permissions': 'sample', 'access_level': 'sample', 'department': 'sample', 'is_active': True}
    resp = client.post("/v1/role_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('role_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('role_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/role_management")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('role_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('role_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('role_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/role_management/{item_id}")
                if got.status_code != 200:
                    failures.append('role_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/role_management/999999")
                if missing.status_code != 404:
                    failures.append('role_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'dimension': 'sample'}
    resp = client.post("/v1/clinic_analytics", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('clinic_analytics: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('clinic_analytics rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/clinic_analytics")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('clinic_analytics list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('clinic_analytics list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('clinic_analytics accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/clinic_analytics/{item_id}")
                if got.status_code != 200:
                    failures.append('clinic_analytics get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/clinic_analytics/999999")
                if missing.status_code != 404:
                    failures.append('clinic_analytics missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
