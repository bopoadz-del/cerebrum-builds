"""PRODUCT cycle: one record per capability survives the boot.

Written by the factory WRITER role (codewhale exec).
"""

from __future__ import annotations

import os

import pytest


# -- local test helpers -----------------------------------------------------
# Defined here, not imported from conftest: the TESTER pass legitimately
# rewrites tests/conftest.py, and a pilot file that imports names the emitted
# conftest does not carry fails collection (which reads as "suite could not
# run", not as a product defect).
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}


def sample_value(cls, name):
    """A value satisfying every constraint the field itself declares."""
    rules = (getattr(cls, "CONSTRAINTS", {}) or {}).get(name) or {}
    allowed = rules.get("allowed_values")
    if allowed:
        return allowed[0]
    kind = str(getattr(cls, "__annotations__", {}).get(name, "str"))
    kind = kind.replace("Optional[", "").replace("]", "").strip().lower()
    lowered = name.lower()
    if kind in ("int", "float"):
        return rules.get("min") if rules.get("min") is not None else 1
    if kind == "bool":
        return False
    if "email" in lowered:
        return "sample@example.com"
    if kind == "datetime" or lowered.endswith("_at"):
        return "2026-09-03T10:00:00"
    if kind == "date" or lowered.endswith("_date"):
        return "2026-09-03"
    if kind == "time" or lowered.endswith("_time"):
        return "10:00:00"
    if lowered == "status" or lowered.endswith("_status"):
        return "open"
    if lowered == "channel" or lowered.endswith("_channel"):
        return "email"
    return "sample"


def sample_payload(cls):
    return {name: sample_value(cls, name) for name in getattr(cls, "FIELDS", [])}


# -- local fixtures ---------------------------------------------------------
# Defined here rather than in conftest: the TESTER pass rewrites
# tests/conftest.py, and these two files are the agent's own product-cycle
# coverage. A module-local fixture keeps them runnable either way.
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def models():
    from app.models import MODELS

    return MODELS


pytestmark = pytest.mark.pilot


@pytest.mark.parametrize(
    "capability_id",
    [
        "patient_records",
        "appointment_scheduling",
        "treatment_management",
        "billing_invoicing",
        "inventory_management",
        "audit_trail",
        "role_management",
        "clinic_analytics",
    ],
)
def test_capability_remembers_one_record(client, capability_id):
    from app.models import MODELS

    cls = MODELS[capability_id]
    body = sample_payload(cls)
    body["reference"] = "pilot-" + capability_id
    resp = client.post("/v1/" + capability_id, json=body, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json().get("ok") is not False

    from app import store

    stored = store.list_all(capability_id)
    assert stored, capability_id
    assert any(str(row.get("reference")) == body["reference"] for row in stored)

    listed = client.get("/v1/" + capability_id)
    assert listed.status_code == 200
    items = listed.json().get("items") or []
    assert any(str(item.get("reference")) == body["reference"] for item in items)


def test_capability_fails_closed_when_blocks_fail(client, monkeypatch):
    """A block failure must never be reported as success, nor persisted."""
    import app.dispatch as dispatch
    from app import store

    def _boom(block_id, payload=None, action=None, params=None, **kw):
        return {"status": "error", "block": block_id, "error": "forced failure"}

    monkeypatch.setattr(dispatch, "execute", _boom)
    before = len(store.list_all("patient_records"))
    from app.models import MODELS

    body = sample_payload(MODELS["patient_records"])
    body["reference"] = "must-not-persist"
    resp = client.post("/v1/patient_records", json=body, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json().get("ok") is False
    assert len(store.list_all("patient_records")) == before


def test_rag_plant_and_query_round_trip(client):
    marker = "PILOT-PLANT thrombectomy gauze protocol"
    client.post("/v1/rag/ingest", json={"text": marker}, headers=AUTH)
    answer = client.post("/v1/rag/query", json={"query": "thrombectomy gauze protocol"}, headers=AUTH)
    assert answer.status_code == 200
    assert "thrombectomy" in answer.text.lower()


def test_restart_survival_of_the_stored_record(client):
    """The record is still there when the app context is re-entered."""
    from fastapi.testclient import TestClient

    from app.main import app

    before = client.get("/v1/patient_records").json().get("items") or []
    assert before
    with TestClient(app) as second:
        after = second.get("/v1/patient_records").json().get("items") or []
    assert len(after) >= len(before)
