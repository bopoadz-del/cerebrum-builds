"""Counter-cases: what each capability REFUSES.

Written by the factory TESTER role. The floor (negative_floor) requires four
per capability; these four are derived from each capability's own spec. Add
the domain cases the brief implies -- the boundary of a rule, a state machine
that must not skip a step -- they count toward the same floor.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}
OTHER_TENANT = {
    "Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN_B", "dev-local-token-b")
}

REFUSED = (400, 403, 404, 409, 422)


def _refused(response):
    """A refusal, by status or by the envelope's own ok:false."""
    if response.status_code in REFUSED:
        return True
    if response.status_code != 200:
        return False
    try:
        body = response.json()
    except Exception:
        return False
    return isinstance(body, dict) and body.get("ok") is False



# -- document_and_knowledge_answers ------------------------------


def test_document_and_knowledge_answers_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'title': 'sample', 'document_kind': 'manual', 'question': 'sample', 'document_text': 'sample', 'attachment_path': 'sample', 'answer': 'sample', 'source_document': 'sample', 'authority_label': 'certified', 'notes': 'sample'}
    resp = client.post("/v1/document_and_knowledge_answers", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "document_and_knowledge_answers accepted a payload with no reference: " + resp.text[:200]
    )


def test_document_and_knowledge_answers_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'title': 'sample', 'document_kind': 'manual', 'question': 'sample', 'document_text': 'sample', 'attachment_path': 'sample', 'answer': 'sample', 'source_document': 'sample', 'authority_label': 'certified', 'notes': 'sample'}
    resp = client.post("/v1/document_and_knowledge_answers", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "document_and_knowledge_answers accepted an undeclared status: " + resp.text[:200]
    )


def test_document_and_knowledge_answers_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'document_kind': 'manual', 'question': 'sample', 'document_text': 'sample', 'attachment_path': 'sample', 'answer': 'sample', 'source_document': 'sample', 'authority_label': 'certified', 'notes': 'sample'}
    made = client.post("/v1/document_and_knowledge_answers", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/document_and_knowledge_answers/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "document_and_knowledge_answers answered %s to another tenant, not 404" % other.status_code
    )


def test_document_and_knowledge_answers_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/document_and_knowledge_answers", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "document_and_knowledge_answers raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "document_and_knowledge_answers accepted malformed input %r" % (junk,)
        )


# -- external_integration_adapter --------------------------------


def test_external_integration_adapter_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'system': 'opera', 'resource': 'sample', 'direction': 'inbound', 'payload_format': 'json', 'endpoint_url': 'sample', 'records_seen': 1, 'notes': 'sample'}
    resp = client.post("/v1/external_integration_adapter", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "external_integration_adapter accepted a payload with no reference: " + resp.text[:200]
    )


def test_external_integration_adapter_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'system': 'opera', 'resource': 'sample', 'direction': 'inbound', 'payload_format': 'json', 'endpoint_url': 'sample', 'records_seen': 1, 'notes': 'sample'}
    resp = client.post("/v1/external_integration_adapter", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "external_integration_adapter accepted an undeclared status: " + resp.text[:200]
    )


def test_external_integration_adapter_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'system': 'opera', 'resource': 'sample', 'direction': 'inbound', 'payload_format': 'json', 'endpoint_url': 'sample', 'records_seen': 1, 'notes': 'sample'}
    made = client.post("/v1/external_integration_adapter", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/external_integration_adapter/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "external_integration_adapter answered %s to another tenant, not 404" % other.status_code
    )


def test_external_integration_adapter_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/external_integration_adapter", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "external_integration_adapter raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "external_integration_adapter accepted malformed input %r" % (junk,)
        )


# -- front_desk_and_guest_stay -----------------------------------


def test_front_desk_and_guest_stay_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'guest_name': 'sample', 'room_number': 'sample', 'arrival_date': '2026-09-03', 'departure_date': '2026-09-03', 'guests_count': 1, 'stay_status': 'reserved', 'folio_currency': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/front_desk_and_guest_stay", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "front_desk_and_guest_stay accepted a payload with no reference: " + resp.text[:200]
    )


def test_front_desk_and_guest_stay_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'guest_name': 'sample', 'room_number': 'sample', 'arrival_date': '2026-09-03', 'departure_date': '2026-09-03', 'guests_count': 1, 'stay_status': 'reserved', 'folio_currency': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/front_desk_and_guest_stay", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "front_desk_and_guest_stay accepted an undeclared status: " + resp.text[:200]
    )


def test_front_desk_and_guest_stay_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'room_number': 'sample', 'arrival_date': '2026-09-03', 'departure_date': '2026-09-03', 'guests_count': 1, 'stay_status': 'reserved', 'folio_currency': 'sample', 'notes': 'sample'}
    made = client.post("/v1/front_desk_and_guest_stay", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/front_desk_and_guest_stay/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "front_desk_and_guest_stay answered %s to another tenant, not 404" % other.status_code
    )


def test_front_desk_and_guest_stay_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/front_desk_and_guest_stay", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "front_desk_and_guest_stay raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "front_desk_and_guest_stay accepted malformed input %r" % (junk,)
        )


# -- guest_engagement_and_segmentation ---------------------------


def test_guest_engagement_and_segmentation_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'guest_name': 'sample', 'recency_days': 1, 'frequency': 1, 'monetary': 1, 'segment': 'champion', 'delivery_channel': 'mcp', 'offer_code': 'id-1', 'notes': 'sample'}
    resp = client.post("/v1/guest_engagement_and_segmentation", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "guest_engagement_and_segmentation accepted a payload with no reference: " + resp.text[:200]
    )


def test_guest_engagement_and_segmentation_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'guest_name': 'sample', 'recency_days': 1, 'frequency': 1, 'monetary': 1, 'segment': 'champion', 'delivery_channel': 'mcp', 'offer_code': 'id-1', 'notes': 'sample'}
    resp = client.post("/v1/guest_engagement_and_segmentation", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "guest_engagement_and_segmentation accepted an undeclared status: " + resp.text[:200]
    )


def test_guest_engagement_and_segmentation_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'recency_days': 1, 'frequency': 1, 'monetary': 1, 'segment': 'champion', 'delivery_channel': 'mcp', 'offer_code': 'id-1', 'notes': 'sample'}
    made = client.post("/v1/guest_engagement_and_segmentation", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/guest_engagement_and_segmentation/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "guest_engagement_and_segmentation answered %s to another tenant, not 404" % other.status_code
    )


def test_guest_engagement_and_segmentation_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/guest_engagement_and_segmentation", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "guest_engagement_and_segmentation raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "guest_engagement_and_segmentation accepted malformed input %r" % (junk,)
        )


# -- housekeeping_and_maintenance --------------------------------


def test_housekeeping_and_maintenance_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'title': 'sample', 'work_type': 'housekeeping', 'room_number': 'sample', 'priority': 'low', 'due_date': '2026-09-03', 'assigned_to': 'sample', 'work_status': 'open', 'notes': 'sample'}
    resp = client.post("/v1/housekeeping_and_maintenance", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "housekeeping_and_maintenance accepted a payload with no reference: " + resp.text[:200]
    )


def test_housekeeping_and_maintenance_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'title': 'sample', 'work_type': 'housekeeping', 'room_number': 'sample', 'priority': 'low', 'due_date': '2026-09-03', 'assigned_to': 'sample', 'work_status': 'open', 'notes': 'sample'}
    resp = client.post("/v1/housekeeping_and_maintenance", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "housekeeping_and_maintenance accepted an undeclared status: " + resp.text[:200]
    )


def test_housekeeping_and_maintenance_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'work_type': 'housekeeping', 'room_number': 'sample', 'priority': 'low', 'due_date': '2026-09-03', 'assigned_to': 'sample', 'work_status': 'open', 'notes': 'sample'}
    made = client.post("/v1/housekeeping_and_maintenance", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/housekeeping_and_maintenance/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "housekeeping_and_maintenance answered %s to another tenant, not 404" % other.status_code
    )


def test_housekeeping_and_maintenance_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/housekeeping_and_maintenance", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "housekeeping_and_maintenance raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "housekeeping_and_maintenance accepted malformed input %r" % (junk,)
        )


# -- operations_billing ------------------------------------------


def test_operations_billing_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'reference': 'sample', 'status': 'open', 'folio_reference': 'sample', 'charge_type': 'room', 'amount': 1, 'currency': 'sample', 'tax_rate_percent': 1, 'total_amount': 1, 'notes': 'sample'}
    resp = client.post("/v1/operations_billing", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "operations_billing accepted a payload with no setting: " + resp.text[:200]
    )


def test_operations_billing_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'setting': 'sample', 'reference': 'sample', 'status': 'not-a-declared-value', 'folio_reference': 'sample', 'charge_type': 'room', 'amount': 1, 'currency': 'sample', 'tax_rate_percent': 1, 'total_amount': 1, 'notes': 'sample'}
    resp = client.post("/v1/operations_billing", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "operations_billing accepted an undeclared status: " + resp.text[:200]
    )


def test_operations_billing_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'setting': 'sample', 'reference': 'sample', 'status': 'open', 'folio_reference': 'sample', 'charge_type': 'room', 'amount': 1, 'currency': 'sample', 'tax_rate_percent': 1, 'total_amount': 1, 'notes': 'sample'}
    made = client.post("/v1/operations_billing", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/operations_billing/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "operations_billing answered %s to another tenant, not 404" % other.status_code
    )


def test_operations_billing_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/operations_billing", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "operations_billing raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "operations_billing accepted malformed input %r" % (junk,)
        )


# -- operations_oversight_dashboard ------------------------------


def test_operations_oversight_dashboard_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'dashboard_name': 'sample', 'widget': 'occupancy', 'window_days': 1, 'operator_role': 'operator', 'occupancy_percent': 1, 'open_work_orders': 1, 'notes': 'sample'}
    resp = client.post("/v1/operations_oversight_dashboard", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "operations_oversight_dashboard accepted a payload with no reference: " + resp.text[:200]
    )


def test_operations_oversight_dashboard_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'dashboard_name': 'sample', 'widget': 'occupancy', 'window_days': 1, 'operator_role': 'operator', 'occupancy_percent': 1, 'open_work_orders': 1, 'notes': 'sample'}
    resp = client.post("/v1/operations_oversight_dashboard", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "operations_oversight_dashboard accepted an undeclared status: " + resp.text[:200]
    )


def test_operations_oversight_dashboard_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'dashboard_name': 'sample', 'widget': 'occupancy', 'window_days': 1, 'operator_role': 'operator', 'occupancy_percent': 1, 'open_work_orders': 1, 'notes': 'sample'}
    made = client.post("/v1/operations_oversight_dashboard", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/operations_oversight_dashboard/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "operations_oversight_dashboard answered %s to another tenant, not 404" % other.status_code
    )


def test_operations_oversight_dashboard_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/operations_oversight_dashboard", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "operations_oversight_dashboard raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "operations_oversight_dashboard accepted malformed input %r" % (junk,)
        )


# -- property_and_room_registry ----------------------------------


def test_property_and_room_registry_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'property_name': 'sample', 'building': 'sample', 'floor': 1, 'room_number': 'sample', 'room_type': 'standard', 'capacity': 1, 'room_status': 'available', 'notes': 'sample'}
    resp = client.post("/v1/property_and_room_registry", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "property_and_room_registry accepted a payload with no reference: " + resp.text[:200]
    )


def test_property_and_room_registry_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'property_name': 'sample', 'building': 'sample', 'floor': 1, 'room_number': 'sample', 'room_type': 'standard', 'capacity': 1, 'room_status': 'available', 'notes': 'sample'}
    resp = client.post("/v1/property_and_room_registry", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "property_and_room_registry accepted an undeclared status: " + resp.text[:200]
    )


def test_property_and_room_registry_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'property_name': 'sample', 'building': 'sample', 'floor': 1, 'room_number': 'sample', 'room_type': 'standard', 'capacity': 1, 'room_status': 'available', 'notes': 'sample'}
    made = client.post("/v1/property_and_room_registry", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/property_and_room_registry/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "property_and_room_registry answered %s to another tenant, not 404" % other.status_code
    )


def test_property_and_room_registry_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/property_and_room_registry", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "property_and_room_registry raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "property_and_room_registry accepted malformed input %r" % (junk,)
        )
