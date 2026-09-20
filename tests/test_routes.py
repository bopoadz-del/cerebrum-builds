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
    payload = {'job_code': 'id-1', 'job_name': 'sample', 'reference': 'sample', 'site_name': 'sample', 'status': 'open', 'client_name': 'sample', 'work_front': 'sample', 'contract_value_aed': 'sample', 'progress_percent': 'sample', 'milestone': 'sample', 'milestone_due_date': '2026-09-03', 'snag_open_count': 1, 'variation_reference': 'sample', 'variation_status': 'draft', 'notes': 'sample'}
    resp = client.post("/v1/job_and_site_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('job_and_site_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('job_and_site_tracking: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('job_and_site_tracking: JSON body is not a dict')
            listed = client.get("/v1/job_and_site_tracking", headers=AUTH)
            if listed.status_code != 200:
                failures.append('job_and_site_tracking list: HTTP ' + str(listed.status_code))

    payload = {'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'valuation_number': 'sample', 'boq_item': 'sample', 'measured_quantity': 'sample', 'unit_rate_aed': 'sample', 'gross_value_aed': 'sample', 'retention_percent': 'sample', 'retention_aed': 'sample', 'vat_rate_percent': 'sample', 'vat_amount_aed': 'sample', 'certified_value_aed': 'sample', 'payment_status': 'unpaid', 'purchase_order': 'sample', 'po_party_type': 'supplier', 'amount_due_aed': 'sample', 'due_on': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/commercials_and_valuations", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('commercials_and_valuations: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('commercials_and_valuations: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('commercials_and_valuations: JSON body is not a dict')
            listed = client.get("/v1/commercials_and_valuations", headers=AUTH)
            if listed.status_code != 200:
                failures.append('commercials_and_valuations list: HTTP ' + str(listed.status_code))

    payload = {'document_title': 'sample', 'document_type': 'boq', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'revision': 'sample', 'file_name': 'sample', 'file_path': 'sample', 'file_sha256': 'sample', 'question': 'sample', 'answer': 'sample', 'source_reference': 'sample', 'indexed_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/document_qa_and_indexing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_qa_and_indexing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('document_qa_and_indexing: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('document_qa_and_indexing: JSON body is not a dict')
            listed = client.get("/v1/document_qa_and_indexing", headers=AUTH)
            if listed.status_code != 200:
                failures.append('document_qa_and_indexing list: HTTP ' + str(listed.status_code))

    payload = {'document_title': 'sample', 'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'method_statement_ref': 'sample', 'work_front': 'sample', 'checklist_item': 'sample', 'checklist_state': 'met', 'readiness_gate': 'ready', 'incident_type': 'near_miss', 'incident_date': '2026-09-03', 'severity': 'low', 'action_taken': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/safety_and_compliance", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('safety_and_compliance: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('safety_and_compliance: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('safety_and_compliance: JSON body is not a dict')
            listed = client.get("/v1/safety_and_compliance", headers=AUTH)
            if listed.status_code != 200:
                failures.append('safety_and_compliance list: HTTP ' + str(listed.status_code))

    payload = {'margin_percent': 'sample', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'report_date': '2026-09-03', 'progress_percent': 'sample', 'certified_value_aed': 'sample', 'cost_to_date_aed': 'sample', 'variations_pending': 'sample', 'snags_open': 'sample', 'payments_due_aed': 'sample', 'summary': 'sample'}
    resp = client.post("/v1/progress_cost_dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('progress_cost_dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('progress_cost_dashboard: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('progress_cost_dashboard: JSON body is not a dict')
            listed = client.get("/v1/progress_cost_dashboard", headers=AUTH)
            if listed.status_code != 200:
                failures.append('progress_cost_dashboard list: HTTP ' + str(listed.status_code))

    payload = {'job_code': 'id-1', 'reference': 'sample', 'reminder_type': 'valuation_due', 'status': 'open', 'due_date': '2026-09-03', 'threshold_count': 1, 'actual_count': 1, 'escalation_state': 'none', 'channel': 'email', 'recipient_email': 'guest@example.com', 'message_body': 'sample', 'schedule': 'monthly', 'summary': 'sample'}
    resp = client.post("/v1/automation_reminders_escalation", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('automation_reminders_escalation: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('automation_reminders_escalation: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('automation_reminders_escalation: JSON body is not a dict')
            listed = client.get("/v1/automation_reminders_escalation", headers=AUTH)
            if listed.status_code != 200:
                failures.append('automation_reminders_escalation list: HTTP ' + str(listed.status_code))

    payload = {'action_type': 'approval', 'actor_name': 'sample', 'actor_role': 'owner', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_reference': 'sample', 'change_summary': 'sample', 'approval_state': 'pending', 'occurred_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/audit_and_access_control", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit_and_access_control: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('audit_and_access_control: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('audit_and_access_control: JSON body is not a dict')
            listed = client.get("/v1/audit_and_access_control", headers=AUTH)
            if listed.status_code != 200:
                failures.append('audit_and_access_control list: HTTP ' + str(listed.status_code))

    payload = {'message_body': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'recipient_email': 'guest@example.com', 'recipient_role': 'owner', 'channel': 'email', 'notification_type': 'approval', 'related_reference': 'sample', 'send_at': '2026-09-03T10:00:00', 'delivery_state': 'queued'}
    resp = client.post("/v1/team_notifications", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('team_notifications: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('team_notifications: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('team_notifications: JSON body is not a dict')
            listed = client.get("/v1/team_notifications", headers=AUTH)
            if listed.status_code != 200:
                failures.append('team_notifications list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'job_code': 'id-1', 'job_name': 'sample', 'reference': 'sample', 'site_name': 'sample', 'status': 'open', 'client_name': 'sample', 'work_front': 'sample', 'contract_value_aed': 'sample', 'progress_percent': 'sample', 'milestone': 'sample', 'milestone_due_date': '2026-09-03', 'snag_open_count': 1, 'variation_reference': 'sample', 'variation_status': 'draft', 'notes': 'sample'}
    resp = client.post("/v1/job_and_site_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('job_and_site_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('job_and_site_tracking rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/job_and_site_tracking", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('job_and_site_tracking list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('job_and_site_tracking list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('job_and_site_tracking accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/job_and_site_tracking/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('job_and_site_tracking get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/job_and_site_tracking/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('job_and_site_tracking missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'valuation_number': 'sample', 'boq_item': 'sample', 'measured_quantity': 'sample', 'unit_rate_aed': 'sample', 'gross_value_aed': 'sample', 'retention_percent': 'sample', 'retention_aed': 'sample', 'vat_rate_percent': 'sample', 'vat_amount_aed': 'sample', 'certified_value_aed': 'sample', 'payment_status': 'unpaid', 'purchase_order': 'sample', 'po_party_type': 'supplier', 'amount_due_aed': 'sample', 'due_on': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/commercials_and_valuations", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('commercials_and_valuations: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('commercials_and_valuations rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/commercials_and_valuations", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('commercials_and_valuations list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('commercials_and_valuations list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('commercials_and_valuations accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/commercials_and_valuations/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('commercials_and_valuations get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/commercials_and_valuations/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('commercials_and_valuations missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'document_title': 'sample', 'document_type': 'boq', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'revision': 'sample', 'file_name': 'sample', 'file_path': 'sample', 'file_sha256': 'sample', 'question': 'sample', 'answer': 'sample', 'source_reference': 'sample', 'indexed_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/document_qa_and_indexing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_qa_and_indexing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('document_qa_and_indexing rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/document_qa_and_indexing", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('document_qa_and_indexing list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('document_qa_and_indexing list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('document_qa_and_indexing accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/document_qa_and_indexing/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('document_qa_and_indexing get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/document_qa_and_indexing/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('document_qa_and_indexing missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'document_title': 'sample', 'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'method_statement_ref': 'sample', 'work_front': 'sample', 'checklist_item': 'sample', 'checklist_state': 'met', 'readiness_gate': 'ready', 'incident_type': 'near_miss', 'incident_date': '2026-09-03', 'severity': 'low', 'action_taken': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/safety_and_compliance", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('safety_and_compliance: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('safety_and_compliance rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/safety_and_compliance", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('safety_and_compliance list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('safety_and_compliance list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('safety_and_compliance accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/safety_and_compliance/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('safety_and_compliance get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/safety_and_compliance/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('safety_and_compliance missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'margin_percent': 'sample', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'report_date': '2026-09-03', 'progress_percent': 'sample', 'certified_value_aed': 'sample', 'cost_to_date_aed': 'sample', 'variations_pending': 'sample', 'snags_open': 'sample', 'payments_due_aed': 'sample', 'summary': 'sample'}
    resp = client.post("/v1/progress_cost_dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('progress_cost_dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('progress_cost_dashboard rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/progress_cost_dashboard", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('progress_cost_dashboard list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('progress_cost_dashboard list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('progress_cost_dashboard accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/progress_cost_dashboard/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('progress_cost_dashboard get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/progress_cost_dashboard/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('progress_cost_dashboard missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'job_code': 'id-1', 'reference': 'sample', 'reminder_type': 'valuation_due', 'status': 'open', 'due_date': '2026-09-03', 'threshold_count': 1, 'actual_count': 1, 'escalation_state': 'none', 'channel': 'email', 'recipient_email': 'guest@example.com', 'message_body': 'sample', 'schedule': 'monthly', 'summary': 'sample'}
    resp = client.post("/v1/automation_reminders_escalation", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('automation_reminders_escalation: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('automation_reminders_escalation rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/automation_reminders_escalation", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('automation_reminders_escalation list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('automation_reminders_escalation list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('automation_reminders_escalation accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/automation_reminders_escalation/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('automation_reminders_escalation get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/automation_reminders_escalation/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('automation_reminders_escalation missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'action_type': 'approval', 'actor_name': 'sample', 'actor_role': 'owner', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_reference': 'sample', 'change_summary': 'sample', 'approval_state': 'pending', 'occurred_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/audit_and_access_control", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit_and_access_control: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('audit_and_access_control rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/audit_and_access_control", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('audit_and_access_control list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('audit_and_access_control list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('audit_and_access_control accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/audit_and_access_control/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('audit_and_access_control get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/audit_and_access_control/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('audit_and_access_control missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'message_body': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'recipient_email': 'guest@example.com', 'recipient_role': 'owner', 'channel': 'email', 'notification_type': 'approval', 'related_reference': 'sample', 'send_at': '2026-09-03T10:00:00', 'delivery_state': 'queued'}
    resp = client.post("/v1/team_notifications", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('team_notifications: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('team_notifications rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/team_notifications", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('team_notifications list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('team_notifications list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('team_notifications accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/team_notifications/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('team_notifications get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/team_notifications/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('team_notifications missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
