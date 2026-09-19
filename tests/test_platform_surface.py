"""The HTTP surface answers, remembers what it is told, and refuses properly."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import MODELS

AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _value(cls, name):
    constraints = getattr(cls, "CONSTRAINTS", {}).get(name, {})
    allowed = constraints.get("allowed_values")
    if allowed:
        return allowed[0]
    kind = str(getattr(cls, "__annotations__", {}).get(name, "str")).strip()
    if kind == "int":
        return int(constraints.get("min", 1))
    if kind == "float":
        return float(constraints.get("min", 1.0))
    if kind == "bool":
        return False
    lowered = name.lower()
    if "email" in lowered:
        return "sample@example.com"
    if lowered.endswith("_at") or lowered.endswith("_datetime"):
        return "2026-09-03T10:00:00"
    if lowered.endswith("_date"):
        return "2026-09-03"
    if lowered.endswith("_time"):
        return "10:00:00"
    return "sample"


def _payload(cls):
    return {name: _value(cls, name) for name in cls.FIELDS}


def test_health_reports_its_checks(client):
    body = client.get("/health").json()
    names = {check["name"] for check in body["checks"]}
    assert {"process", "persistent_disk", "database", "migrations"} <= names


def test_every_capability_is_served(client):
    ids = {item["id"] for item in client.get("/v1/capabilities").json()["items"]}
    assert ids == set(MODELS)


@pytest.mark.parametrize("capability_id", sorted(MODELS))
def test_capability_round_trip(client, capability_id):
    """POST creates the record; the list route hands it back."""
    cls = MODELS[capability_id]
    created = client.post(f"/v1/{capability_id}", json=_payload(cls), headers=AUTH)
    assert created.status_code == 200, created.text[:300]
    body = created.json()
    assert body.get("ok") is not False, body.get("error")

    listed = client.get(f"/v1/{capability_id}", headers=AUTH)
    assert listed.status_code == 200
    rows = listed.json()["items"]
    assert rows, "the platform accepted a record it did not remember"
    assert rows[0]["reference"] == "sample"


def test_write_requires_a_token(client):
    assert client.post("/v1/budget_planning_tracking", json={}).status_code == 401


def test_unknown_enum_is_refused(client):
    cls = MODELS["budget_planning_tracking"]
    payload = _payload(cls)
    payload["status"] = "not-a-status"
    assert client.post("/v1/budget_planning_tracking", json=payload, headers=AUTH).status_code == 422


def test_missing_required_field_is_refused(client):
    assert client.post("/v1/budget_planning_tracking", json={}, headers=AUTH).status_code == 422


def test_unknown_record_is_404(client):
    assert client.get("/v1/approval_workflow/999999", headers=AUTH).status_code == 404
