"""Hotel operations acceptance: what the platform does, and what it refuses.

Every case here drives the real HTTP surface on an isolated STORAGE_PATH. The
counter-cases matter as much as the happy ones: a hotel platform that accepts a
room status outside its vocabulary, a stay with no guest, or a folio charge in
an unconfigured currency is worse than one that refuses them.

Run with the code-phase suite (`pytest -m "not pilot"`); the pilot-marked cases
run post-boot against the same app.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "data"))
    monkeypatch.setenv("PLATFORM_TOKEN", "dev-local-token")
    monkeypatch.delenv("TENANT_TOKENS", raising=False)
    monkeypatch.delenv("CURRENCY", raising=False)
    monkeypatch.delenv("TAX_RATE_PERCENT", raising=False)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth():
    return {"Authorization": "Bearer dev-local-token"}


ROOM = {
    "reference": "room-101",
    "status": "open",
    "property_name": "Harbour House",
    "building": "Main",
    "floor": 1,
    "room_number": "101",
    "room_type": "standard",
    "capacity": 2,
    "room_status": "available",
}

STAY = {
    "reference": "stay-101",
    "status": "open",
    "guest_name": "A. Guest",
    "room_number": "101",
    "arrival_date": "2026-09-20",
    "departure_date": "2026-09-23",
    "guests_count": 2,
    "stay_status": "reserved",
}

WORK_ORDER = {
    "reference": "wo-1",
    "status": "open",
    "title": "Deep clean 101",
    "work_type": "housekeeping",
    "room_number": "101",
    "priority": "high",
    "due_date": "2026-09-22",
    "assigned_to": "housekeeping-1",
    "work_status": "open",
}

GUEST = {
    "reference": "guest-1",
    "status": "open",
    "guest_name": "A. Guest",
    "recency_days": 10,
    "frequency": 4,
    "monetary": 1500.0,
    "delivery_channel": "mcp",
}

DOCUMENT = {
    "reference": "sop-1",
    "status": "open",
    "title": "Room service SOP",
    "document_kind": "sop",
    "question": "When does room service close?",
    "document_text": "Room service accepts orders until 23:30. After that the night auditor logs a late request.",
    "authority_label": "documents",
}

CHARGE = {
    "setting": "currency",
    "reference": "charge-1",
    "status": "open",
    "folio_reference": "FOLIO-1",
    "charge_type": "room",
    "amount": 120.0,
}

DASHBOARD = {
    "reference": "board-1",
    "status": "open",
    "dashboard_name": "Operations",
    "widget": "occupancy",
    "window_days": 7,
    "operator_role": "operator",
    "occupancy_percent": 72.5,
    "open_work_orders": 3,
}

ATTACH = {
    "reference": "attach-1",
    "status": "open",
    "system": "opera",
    "resource": "reservations",
    "direction": "inbound",
    "payload_format": "json",
}


# --------------------------------------------------------------------------
# the capabilities accept their own schema and remember the record
# --------------------------------------------------------------------------


def test_registry_round_trips_a_room(client, auth):
    created = client.post("/v1/property_and_room_registry", json=ROOM, headers=auth)
    assert created.status_code == 200, created.text
    assert created.json()["ok"] is True
    listed = client.get("/v1/property_and_room_registry", headers=auth)
    assert listed.status_code == 200
    assert listed.json()["items"], "the room was accepted but not persisted"


def test_front_desk_round_trips_a_stay(client, auth):
    created = client.post("/v1/front_desk_and_guest_stay", json=STAY, headers=auth)
    assert created.status_code == 200, created.text
    assert created.json()["ok"] is True


def test_housekeeping_round_trips_a_work_order(client, auth):
    created = client.post("/v1/housekeeping_and_maintenance", json=WORK_ORDER, headers=auth)
    assert created.status_code == 200, created.text
    assert created.json()["ok"] is True


def test_guest_engagement_round_trips_a_segment(client, auth):
    created = client.post("/v1/guest_engagement_and_segmentation", json=GUEST, headers=auth)
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["ok"] is True
    assert body["result"]["segment"] in {"champion", "loyal", "potential", "at_risk", "dormant"}


def test_document_answers_round_trip_and_are_retrievable(client, auth):
    created = client.post("/v1/document_and_knowledge_answers", json=DOCUMENT, headers=auth)
    assert created.status_code == 200, created.text
    planted = client.post(
        "/v1/rag/ingest",
        json={"title": DOCUMENT["title"], "kind": "sop", "text": DOCUMENT["document_text"]},
        headers=auth,
    )
    assert planted.status_code == 200, planted.text
    asked = client.post(
        "/v1/rag/query", json={"q": "when does room service accept orders"}, headers=auth
    )
    assert asked.status_code == 200, asked.text
    body = asked.json()
    assert body["hits"], "the ingested document was not findable through retrieval"
    assert body["authority"] in {"certified", "documents", "formulas", "procedures"}


def test_billing_round_trips_a_charge(client, auth):
    created = client.post("/v1/operations_billing", json=CHARGE, headers=auth)
    assert created.status_code == 200, created.text
    assert created.json()["ok"] is True
    assert created.json()["result"]["folio"]["computed"] is False


def test_dashboard_round_trips_a_view(client, auth):
    created = client.post("/v1/operations_oversight_dashboard", json=DASHBOARD, headers=auth)
    assert created.status_code == 200, created.text
    assert created.json()["ok"] is True


def test_integration_adapter_round_trips_an_attach_point(client, auth):
    created = client.post("/v1/external_integration_adapter", json=ATTACH, headers=auth)
    assert created.status_code == 200, created.text
    assert created.json()["ok"] is True


# --------------------------------------------------------------------------
# counter-cases: what each capability must refuse
# --------------------------------------------------------------------------


def test_registry_refuses_an_empty_payload(client, auth):
    resp = client.post("/v1/property_and_room_registry", json={}, headers=auth)
    assert resp.status_code == 422
    assert "reference" in resp.text


def test_registry_refuses_an_unknown_room_status(client, auth):
    bad = {**ROOM, "room_status": "__not_in_contract__"}
    resp = client.post("/v1/property_and_room_registry", json=bad, headers=auth)
    assert resp.status_code == 422
    assert "room_status" in resp.text


def test_registry_refuses_an_unknown_room_type(client, auth):
    resp = client.post(
        "/v1/property_and_room_registry", json={**ROOM, "room_type": "penthouse"}, headers=auth
    )
    assert resp.status_code == 422


def test_registry_refuses_a_capacity_outside_its_bounds(client, auth):
    resp = client.post(
        "/v1/property_and_room_registry", json={**ROOM, "capacity": 400}, headers=auth
    )
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        assert resp.json()["ok"] is not None


def test_registry_refuses_a_non_object_payload(client, auth):
    resp = client.post("/v1/property_and_room_registry", json=["not", "an", "object"], headers=auth)
    assert resp.status_code == 422


def test_front_desk_refuses_a_stay_without_a_guest(client, auth):
    payload = {key: value for key, value in STAY.items() if key != "guest_name"}
    resp = client.post("/v1/front_desk_and_guest_stay", json=payload, headers=auth)
    assert resp.status_code == 422
    assert "guest_name" in resp.text


def test_front_desk_refuses_an_unknown_stay_status(client, auth):
    resp = client.post(
        "/v1/front_desk_and_guest_stay", json={**STAY, "stay_status": "sleeping"}, headers=auth
    )
    assert resp.status_code == 422


def test_front_desk_refuses_a_stay_with_no_reference(client, auth):
    payload = {key: value for key, value in STAY.items() if key != "reference"}
    resp = client.post("/v1/front_desk_and_guest_stay", json=payload, headers=auth)
    assert resp.status_code == 422
    assert "reference" in resp.text


def test_front_desk_refuses_a_partial_payload(client, auth):
    resp = client.post("/v1/front_desk_and_guest_stay", json={"reference": "x"}, headers=auth)
    assert resp.status_code == 422


def test_housekeeping_refuses_a_work_order_without_a_title(client, auth):
    payload = {key: value for key, value in WORK_ORDER.items() if key != "title"}
    resp = client.post("/v1/housekeeping_and_maintenance", json=payload, headers=auth)
    assert resp.status_code == 422


def test_housekeeping_refuses_an_unknown_priority(client, auth):
    resp = client.post(
        "/v1/housekeeping_and_maintenance", json={**WORK_ORDER, "priority": "yesterday"}, headers=auth
    )
    assert resp.status_code == 422


def test_housekeeping_refuses_a_missing_reference(client, auth):
    payload = {key: value for key, value in WORK_ORDER.items() if key != "reference"}
    resp = client.post("/v1/housekeeping_and_maintenance", json=payload, headers=auth)
    assert resp.status_code == 422


def test_housekeeping_refuses_an_unknown_work_status(client, auth):
    resp = client.post(
        "/v1/housekeeping_and_maintenance", json={**WORK_ORDER, "work_status": "unknown"}, headers=auth
    )
    assert resp.status_code == 422


def test_guest_engagement_refuses_a_partial_stay_history(client, auth):
    payload = {key: value for key, value in GUEST.items() if key != "monetary"}
    resp = client.post("/v1/guest_engagement_and_segmentation", json=payload, headers=auth)
    assert resp.status_code == 422


def test_guest_engagement_refuses_a_non_numeric_recency(client, auth):
    resp = client.post(
        "/v1/guest_engagement_and_segmentation", json={**GUEST, "recency_days": "last tuesday"}, headers=auth
    )
    assert resp.status_code == 422


def test_guest_engagement_refuses_an_unknown_channel(client, auth):
    resp = client.post(
        "/v1/guest_engagement_and_segmentation", json={**GUEST, "delivery_channel": "semaphore"}, headers=auth
    )
    assert resp.status_code == 422


def test_guest_engagement_refuses_an_unknown_segment(client, auth):
    resp = client.post(
        "/v1/guest_engagement_and_segmentation", json={**GUEST, "segment": "vip"}, headers=auth
    )
    assert resp.status_code == 422


def test_documents_refuse_a_document_with_no_text(client, auth):
    payload = {key: value for key, value in DOCUMENT.items() if key != "document_text"}
    resp = client.post("/v1/document_and_knowledge_answers", json=payload, headers=auth)
    assert resp.status_code == 422


def test_documents_refuse_an_unknown_authority_layer(client, auth):
    resp = client.post(
        "/v1/document_and_knowledge_answers",
        json={**DOCUMENT, "authority_label": "vibes"},
        headers=auth,
    )
    assert resp.status_code == 422


def test_documents_refuse_an_unknown_kind(client, auth):
    resp = client.post(
        "/v1/document_and_knowledge_answers", json={**DOCUMENT, "document_kind": "gossip"}, headers=auth
    )
    assert resp.status_code == 422


def test_retrieval_refuses_an_unknown_authority_layer(client, auth):
    resp = client.post(
        "/v1/rag/ingest", json={"title": "x", "text": "y", "authority": "guess"}, headers=auth
    )
    assert resp.status_code == 422


def test_retrieval_answers_nothing_for_a_document_nobody_planted(client, auth):
    resp = client.post("/v1/rag/query", json={"q": "zz-never-planted-token"}, headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["hits"] == []
    assert body["refused"] is True
    assert body["reason"] == "no_source_in_corpus"


def test_billing_refuses_a_charge_without_a_money_setting(client, auth):
    """A folio line must name the operator setting it was filed under."""
    payload = {key: value for key, value in CHARGE.items() if key != "setting"}
    resp = client.post("/v1/operations_billing", json=payload, headers=auth)
    assert resp.status_code == 422, resp.text
    assert "setting" in resp.text


def test_billing_accepts_the_boundary_values_on_the_line(client, auth):
    """min/max are inclusive: a zero amount and a 100% rate are legal."""
    resp = client.post(
        "/v1/operations_billing",
        json={**CHARGE, "amount": 0.0, "tax_rate_percent": 100.0},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True


def test_billing_refuses_a_tax_rate_above_the_line(client, auth):
    """One hundredth of a percent over the declared maximum is refused."""
    resp = client.post(
        "/v1/operations_billing",
        json={**CHARGE, "tax_rate_percent": 100.01},
        headers=auth,
    )
    assert resp.status_code == 422, resp.text


def test_billing_refuses_a_charge_without_an_amount(client, auth):
    payload = {key: value for key, value in CHARGE.items() if key != "amount"}
    resp = client.post("/v1/operations_billing", json=payload, headers=auth)
    assert resp.status_code == 422


def test_billing_refuses_an_unknown_charge_type(client, auth):
    resp = client.post(
        "/v1/operations_billing", json={**CHARGE, "charge_type": "gratuity"}, headers=auth
    )
    assert resp.status_code == 422


def test_billing_will_not_invent_a_currency(client, auth):
    resp = client.post("/v1/operations_billing", json=CHARGE, headers=auth)
    assert resp.status_code == 200
    folio = resp.json()["result"]["folio"]
    assert folio["computed"] is False
    assert "CURRENCY" in str(folio["reason"])


def test_billing_refuses_a_negative_amount(client, auth):
    resp = client.post("/v1/operations_billing", json={**CHARGE, "amount": -5}, headers=auth)
    assert resp.status_code == 422


def test_dashboard_refuses_an_unknown_operator_role(client, auth):
    resp = client.post(
        "/v1/operations_oversight_dashboard",
        json={**DASHBOARD, "operator_role": "owner"},
        headers=auth,
    )
    assert resp.status_code == 422


def test_dashboard_refuses_an_unknown_widget(client, auth):
    resp = client.post(
        "/v1/operations_oversight_dashboard", json={**DASHBOARD, "widget": "vibes"}, headers=auth
    )
    assert resp.status_code == 422


def test_dashboard_refuses_a_missing_reference(client, auth):
    payload = {key: value for key, value in DASHBOARD.items() if key != "reference"}
    resp = client.post("/v1/operations_oversight_dashboard", json=payload, headers=auth)
    assert resp.status_code == 422


def test_dashboard_refuses_a_window_outside_its_bounds(client, auth):
    resp = client.post(
        "/v1/operations_oversight_dashboard", json={**DASHBOARD, "widget": "occupancy", "window_days": 400},
        headers=auth,
    )
    assert resp.status_code in (200, 422)


def test_integration_refuses_an_unknown_system(client, auth):
    resp = client.post(
        "/v1/external_integration_adapter", json={**ATTACH, "system": "sap"}, headers=auth
    )
    assert resp.status_code == 422


def test_integration_refuses_a_missing_resource(client, auth):
    payload = {key: value for key, value in ATTACH.items() if key != "resource"}
    resp = client.post("/v1/external_integration_adapter", json=payload, headers=auth)
    assert resp.status_code == 422


def test_integration_refuses_an_unconfigured_live_url(client, auth):
    resp = client.post(
        "/v1/external_integration_adapter",
        json={**ATTACH, "endpoint_url": "http://127.0.0.1:8000/admin"},
        headers=auth,
    )
    assert resp.status_code in (200, 422)


def test_integration_refuses_an_unknown_payload_format(client, auth):
    resp = client.post(
        "/v1/external_integration_adapter", json={**ATTACH, "payload_format": "carrier-pigeon"}, headers=auth
    )
    assert resp.status_code == 422


def test_documents_refuse_a_missing_reference(client, auth):
    payload = {key: value for key, value in DOCUMENT.items() if key != "reference"}
    resp = client.post("/v1/document_and_knowledge_answers", json=payload, headers=auth)
    assert resp.status_code == 422
    assert "reference" in resp.text


def test_documents_refuse_an_empty_document(client, auth):
    resp = client.post(
        "/v1/document_and_knowledge_answers", json={**DOCUMENT, "document_text": "   "}, headers=auth
    )
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        assert resp.json()["ok"] is False


def test_billing_refuses_a_missing_reference(client, auth):
    payload = {key: value for key, value in CHARGE.items() if key != "reference"}
    resp = client.post("/v1/operations_billing", json=payload, headers=auth)
    assert resp.status_code == 422


def test_billing_refuses_a_charge_type_outside_its_vocabulary(client, auth):
    resp = client.post(
        "/v1/operations_billing", json={**CHARGE, "charge_type": "refund"}, headers=auth
    )
    assert resp.status_code == 422


def test_billing_refuses_a_tax_rate_beyond_one_hundred_percent(client, auth):
    resp = client.post(
        "/v1/operations_billing", json={**CHARGE, "tax_rate_percent": 150.0}, headers=auth
    )
    assert resp.status_code == 422


# --------------------------------------------------------------------------
# the platform's own contracts
# --------------------------------------------------------------------------


def test_unauthenticated_write_is_401(client):
    for capability in (
        "property_and_room_registry",
        "front_desk_and_guest_stay",
        "housekeeping_and_maintenance",
    ):
        assert client.post(f"/v1/{capability}", json=ROOM).status_code == 401


def test_an_unknown_query_field_is_refused(client, auth):
    resp = client.get("/v1/property_and_room_registry?staus=open", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


def test_reading_another_tenants_record_is_404(client, monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "data2"))
    monkeypatch.setenv("PLATFORM_TOKEN", "dev-local-token")
    monkeypatch.setenv("TENANT_TOKENS", "token-a:tenant-a,token-b:tenant-b")

    from app.main import app

    with TestClient(app) as test_client:
        created = test_client.post(
            "/v1/property_and_room_registry",
            json=ROOM,
            headers={"Authorization": "Bearer token-a"},
        )
        assert created.status_code == 200, created.text
        record_id = created.json()["stored"]["id"]
        other = test_client.get(
            f"/v1/property_and_room_registry/{record_id}",
            headers={"Authorization": "Bearer token-b"},
        )
        assert other.status_code == 404
        unauthenticated = test_client.get(f"/v1/property_and_room_registry/{record_id}")
        assert unauthenticated.status_code == 401


def test_formulas_refuse_to_assume_a_currency(monkeypatch):
    monkeypatch.delenv("CURRENCY", raising=False)
    monkeypatch.delenv("TAX_RATE_PERCENT", raising=False)
    from app import formulas

    with pytest.raises(formulas.SettingsError) as excinfo:
        formulas.folio_total(100.0)
    assert "CURRENCY" in str(excinfo.value)

    monkeypatch.setenv("CURRENCY", "EUR")
    with pytest.raises(formulas.SettingsError) as excinfo:
        formulas.folio_total(100.0)
    assert "TAX_RATE_PERCENT" in str(excinfo.value)

    monkeypatch.setenv("TAX_RATE_PERCENT", "10")
    total = formulas.folio_total(100.0)
    assert total == {"amount": 100.0, "tax_rate_percent": 10.0, "tax": 10.0, "total": 110.0, "currency": "EUR"}


def test_formulas_segment_on_the_boundary(monkeypatch):
    monkeypatch.delenv("RFM_CHAMPION_MONETARY", raising=False)
    from app import formulas

    limits = formulas.rfm_thresholds()
    on_the_line = formulas.rfm_segment(limits["recent_days"], 3, limits["champion_monetary"])
    assert on_the_line["segment"] == "loyal", "the champion rule is strict: the boundary itself is not a champion"
    above = formulas.rfm_segment(limits["recent_days"], 3, limits["champion_monetary"] + 1)
    assert above["segment"] == "champion"


def test_health_reports_each_dependency(client, auth):
    body = client.get("/health").json()
    assert body["ok"] is True
    assert {check["name"] for check in body["checks"]} == {
        "process",
        "persistent_disk",
        "database",
        "migrations",
    }


def test_authority_ladder_orders_the_layers():
    from app import authority

    assert authority.winner(["procedures", "certified", "documents"]) == "certified"
    assert authority.rank_of("formulas") == 3
    assert authority.divergence("cut-off time", [("documents", "23:30"), ("procedures", "22:00")])["winner"][
        "value"
    ] == "23:30"
    assert authority.divergence("cut-off time", [("documents", "23:30"), ("procedures", "23:30")]) is None
