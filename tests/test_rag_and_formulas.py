"""Document retrieval and the FinOps arithmetic, exercised directly."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app import formulas, retrieval
from app.main import app

AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_ingest_then_query_finds_the_passage(client):
    marker = "ACCEPTANCE-PLANT-finops-invoice the March software invoice is 12000 GBP"
    planted = client.post(
        "/v1/rag/ingest",
        json={"text": marker, "document_type": "invoice", "department": "finance"},
        headers=AUTH,
    )
    assert planted.status_code == 200, planted.text[:200]

    found = client.post("/v1/rag/query", json={"q": "March software invoice"}, headers=AUTH)
    assert found.status_code == 200
    body = found.json()
    assert any("March software invoice" in str(hit.get("text", "")) for hit in body["hits"])


def test_query_for_an_absent_term_returns_nothing(client):
    body = client.get(
        "/v1/rag/query", params={"q": "zzz-not-in-any-document"}, headers=AUTH
    ).json()
    assert body["hits"] == []


def test_retrieval_is_tenant_scoped():
    retrieval.ingest(tenant_id="tenant-a", text="tenant a price list", document="a")
    assert retrieval.search(tenant_id="tenant-b", query="price") == []


def test_finops_formulas():
    assert formulas.budget_utilisation(planned_amount=1000, actual_amount=250) == 25.0
    assert formulas.budget_remaining(planned_amount=1000, actual_amount=250) == 750.0
    assert formulas.budget_overrun(planned_amount=1000, actual_amount=1000) is False
    assert formulas.spend_net(amount=120.0) == 100.0
    assert formulas.spend_vat(amount=120.0) == 20.0
    assert formulas.variance_amount(budget_amount=1000, actual_amount=1150) == 150.0
    assert formulas.variance_percent(budget_amount=1000, actual_amount=1150) == 15.0
    assert formulas.portfolio_total(spend_total=500, commitment_total=250) == 750.0
    assert formulas.portfolio_risk(spend_total=1200, forecast_total=1000) == "high"
    with pytest.raises(formulas.FormulaError):
        formulas.budget_utilisation(planned_amount=0, actual_amount=1)
