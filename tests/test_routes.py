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
    payload = {'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'species': 'dog', 'status': 'open', 'breed': 'sample', 'sex': 'male', 'age_years': 'sample', 'weight_kg': 'sample', 'microchip_id': 'id-1', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'clinical_history': 'sample'}
    resp = client.post("/v1/patient_and_owner_records", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('patient_and_owner_records: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('patient_and_owner_records: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('patient_and_owner_records: JSON body is not a dict')
            listed = client.get("/v1/patient_and_owner_records", headers=AUTH)
            if listed.status_code != 200:
                failures.append('patient_and_owner_records list: HTTP ' + str(listed.status_code))

    payload = {'appointment_type': 'wellness_exam', 'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'veterinarian': 'sample', 'room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'}
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
            listed = client.get("/v1/appointment_scheduling", headers=AUTH)
            if listed.status_code != 200:
                failures.append('appointment_scheduling list: HTTP ' + str(listed.status_code))

    payload = {'diagnosis': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'visit_date': '2026-09-03', 'treatment_plan': 'sample', 'medication': 'sample', 'dosage_mg': 'sample', 'administration_route': 'oral', 'attachment_path': 'sample', 'prescription_notes': 'sample'}
    resp = client.post("/v1/clinical_visit_notes_and_treatment_plans", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('clinical_visit_notes_and_treatment_plans: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('clinical_visit_notes_and_treatment_plans: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('clinical_visit_notes_and_treatment_plans: JSON body is not a dict')
            listed = client.get("/v1/clinical_visit_notes_and_treatment_plans", headers=AUTH)
            if listed.status_code != 200:
                failures.append('clinical_visit_notes_and_treatment_plans list: HTTP ' + str(listed.status_code))

    payload = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'vaccine_type': 'rabies', 'administered_on': 'sample', 'next_due_on': 'sample', 'lot_number': 'sample', 'administered_by': 'sample', 'reminder_channel': 'email'}
    resp = client.post("/v1/vaccination_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('vaccination_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('vaccination_tracking: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('vaccination_tracking: JSON body is not a dict')
            listed = client.get("/v1/vaccination_tracking", headers=AUTH)
            if listed.status_code != 200:
                failures.append('vaccination_tracking list: HTTP ' + str(listed.status_code))

    payload = {'owner_name': 'sample', 'reference': 'sample', 'service_code': 'id-1', 'status': 'open', 'invoice_total': 'sample', 'amount_paid': 'sample', 'currency': 'USD', 'issued_on': 'sample', 'due_on': 'sample', 'payment_method': 'card', 'attachment_path': 'sample'}
    resp = client.post("/v1/billing_and_invoicing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('billing_and_invoicing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('billing_and_invoicing: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('billing_and_invoicing: JSON body is not a dict')
            listed = client.get("/v1/billing_and_invoicing", headers=AUTH)
            if listed.status_code != 200:
                failures.append('billing_and_invoicing list: HTTP ' + str(listed.status_code))

    payload = {'metric_name': 'sample', 'reference': 'sample', 'report_name': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'appointments_count': 1, 'revenue_total': 'sample', 'event_type': 'sample'}
    resp = client.post("/v1/analytics_and_reporting", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('analytics_and_reporting: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('analytics_and_reporting: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('analytics_and_reporting: JSON body is not a dict')
            listed = client.get("/v1/analytics_and_reporting", headers=AUTH)
            if listed.status_code != 200:
                failures.append('analytics_and_reporting list: HTTP ' + str(listed.status_code))

    payload = {'content': 'sample', 'record_type': 'clinical_note', 'reference': 'sample', 'status': 'open', 'subject_ref': 'sample', 'content_hash': 'sample', 'reviewer': 'sample', 'reviewed_on': 'sample', 'retention_until': 'sample'}
    resp = client.post("/v1/compliance_and_audit_trail", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('compliance_and_audit_trail: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('compliance_and_audit_trail: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('compliance_and_audit_trail: JSON body is not a dict')
            listed = client.get("/v1/compliance_and_audit_trail", headers=AUTH)
            if listed.status_code != 200:
                failures.append('compliance_and_audit_trail list: HTTP ' + str(listed.status_code))

    payload = {'owner_name': 'sample', 'reference': 'sample', 'reminder_type': 'appointment_reminder', 'status': 'open', 'owner_email': 'guest@example.com', 'channel': 'email', 'scheduled_for': 'sample', 'template_name': 'sample', 'message_body': 'sample'}
    resp = client.post("/v1/client_communication_and_reminders", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('client_communication_and_reminders: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('client_communication_and_reminders: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('client_communication_and_reminders: JSON body is not a dict')
            listed = client.get("/v1/client_communication_and_reminders", headers=AUTH)
            if listed.status_code != 200:
                failures.append('client_communication_and_reminders list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'species': 'dog', 'status': 'open', 'breed': 'sample', 'sex': 'male', 'age_years': 'sample', 'weight_kg': 'sample', 'microchip_id': 'id-1', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'clinical_history': 'sample'}
    resp = client.post("/v1/patient_and_owner_records", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('patient_and_owner_records: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('patient_and_owner_records rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/patient_and_owner_records", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('patient_and_owner_records list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('patient_and_owner_records list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('patient_and_owner_records accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/patient_and_owner_records/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('patient_and_owner_records get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/patient_and_owner_records/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('patient_and_owner_records missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'appointment_type': 'wellness_exam', 'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'veterinarian': 'sample', 'room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'}
    resp = client.post("/v1/appointment_scheduling", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('appointment_scheduling: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('appointment_scheduling rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/appointment_scheduling", headers=AUTH)
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
                got = client.get(f"/v1/appointment_scheduling/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('appointment_scheduling get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/appointment_scheduling/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('appointment_scheduling missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'diagnosis': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'visit_date': '2026-09-03', 'treatment_plan': 'sample', 'medication': 'sample', 'dosage_mg': 'sample', 'administration_route': 'oral', 'attachment_path': 'sample', 'prescription_notes': 'sample'}
    resp = client.post("/v1/clinical_visit_notes_and_treatment_plans", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('clinical_visit_notes_and_treatment_plans: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('clinical_visit_notes_and_treatment_plans rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/clinical_visit_notes_and_treatment_plans", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('clinical_visit_notes_and_treatment_plans list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('clinical_visit_notes_and_treatment_plans list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('clinical_visit_notes_and_treatment_plans accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/clinical_visit_notes_and_treatment_plans/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('clinical_visit_notes_and_treatment_plans get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/clinical_visit_notes_and_treatment_plans/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('clinical_visit_notes_and_treatment_plans missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'vaccine_type': 'rabies', 'administered_on': 'sample', 'next_due_on': 'sample', 'lot_number': 'sample', 'administered_by': 'sample', 'reminder_channel': 'email'}
    resp = client.post("/v1/vaccination_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('vaccination_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('vaccination_tracking rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/vaccination_tracking", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('vaccination_tracking list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('vaccination_tracking list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('vaccination_tracking accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/vaccination_tracking/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('vaccination_tracking get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/vaccination_tracking/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('vaccination_tracking missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'owner_name': 'sample', 'reference': 'sample', 'service_code': 'id-1', 'status': 'open', 'invoice_total': 'sample', 'amount_paid': 'sample', 'currency': 'USD', 'issued_on': 'sample', 'due_on': 'sample', 'payment_method': 'card', 'attachment_path': 'sample'}
    resp = client.post("/v1/billing_and_invoicing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('billing_and_invoicing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('billing_and_invoicing rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/billing_and_invoicing", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('billing_and_invoicing list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('billing_and_invoicing list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('billing_and_invoicing accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/billing_and_invoicing/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('billing_and_invoicing get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/billing_and_invoicing/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('billing_and_invoicing missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'metric_name': 'sample', 'reference': 'sample', 'report_name': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'appointments_count': 1, 'revenue_total': 'sample', 'event_type': 'sample'}
    resp = client.post("/v1/analytics_and_reporting", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('analytics_and_reporting: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('analytics_and_reporting rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/analytics_and_reporting", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('analytics_and_reporting list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('analytics_and_reporting list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('analytics_and_reporting accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/analytics_and_reporting/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('analytics_and_reporting get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/analytics_and_reporting/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('analytics_and_reporting missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'content': 'sample', 'record_type': 'clinical_note', 'reference': 'sample', 'status': 'open', 'subject_ref': 'sample', 'content_hash': 'sample', 'reviewer': 'sample', 'reviewed_on': 'sample', 'retention_until': 'sample'}
    resp = client.post("/v1/compliance_and_audit_trail", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('compliance_and_audit_trail: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('compliance_and_audit_trail rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/compliance_and_audit_trail", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('compliance_and_audit_trail list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('compliance_and_audit_trail list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('compliance_and_audit_trail accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/compliance_and_audit_trail/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('compliance_and_audit_trail get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/compliance_and_audit_trail/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('compliance_and_audit_trail missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'owner_name': 'sample', 'reference': 'sample', 'reminder_type': 'appointment_reminder', 'status': 'open', 'owner_email': 'guest@example.com', 'channel': 'email', 'scheduled_for': 'sample', 'template_name': 'sample', 'message_body': 'sample'}
    resp = client.post("/v1/client_communication_and_reminders", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('client_communication_and_reminders: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('client_communication_and_reminders rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/client_communication_and_reminders", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('client_communication_and_reminders list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('client_communication_and_reminders list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('client_communication_and_reminders accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/client_communication_and_reminders/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('client_communication_and_reminders get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/client_communication_and_reminders/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('client_communication_and_reminders missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
