"""Document retrieval and the bakery arithmetic, exercised directly."""

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
    marker = "ACCEPTANCE-PLANT-bakery-zone the south branch delivers to Zone 4"
    planted = client.post(
        "/v1/rag/ingest",
        json={"text": marker, "document_type": "delivery_zone"},
        headers=AUTH,
    )
    assert planted.status_code == 200, planted.text[:200]

    found = client.post("/v1/rag/query", json={"q": "Zone 4 delivery"}, headers=AUTH)
    assert found.status_code == 200
    body = found.json()
    assert any("Zone 4" in str(hit.get("text", "")) for hit in body["hits"])


def test_query_for_an_absent_term_returns_nothing(client):
    body = client.get(
        "/v1/rag/query", params={"q": "zzz-not-in-any-document"}, headers=AUTH
    ).json()
    assert body["hits"] == []


def test_retrieval_is_tenant_scoped():
    retrieval.ingest(tenant_id="tenant-a", text="tenant a sourdough recipe", document="a")
    assert retrieval.search(tenant_id="tenant-b", query="sourdough") == []


def test_margin_and_reorder_formulas():
    assert formulas.margin_percent(sale_price=2.5, ingredient_cost=1.0) == 60.0
    assert formulas.reorder_required(quantity_on_hand=4, reorder_threshold=5) is True
    with pytest.raises(formulas.FormulaError):
        formulas.margin_percent(sale_price=0, ingredient_cost=1.0)
    assert formulas.delivery_capacity() == {"cars": 2, "bikes": 10, "vehicles": 12}
