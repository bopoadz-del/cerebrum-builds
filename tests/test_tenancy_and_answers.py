"""Tenancy, precedence.v1, the corpus and the grounded answer path."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

import app.authority as authority
import app.formulas as formulas
import app.llm as llm
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _token(monkeypatch, value: str) -> str:
    monkeypatch.setenv("PLATFORM_TOKEN", value)
    return value


def test_precedence_is_versioned_data():
    body = authority.declaration()
    assert body["version"] == "precedence.v1"
    kinds = [layer["kind"] for layer in body["layers"]]
    assert kinds == ["certified", "document", "formula", "procedure"]


def test_the_winner_is_decided_by_precedence_not_by_confidence():
    claims = [
        {"layer": "procedure", "text": "procedure says X", "confidence": 0.99},
        {"layer": "certified", "text": "certificate says Y", "confidence": 0.10},
    ]
    top = authority.winner(claims)
    assert top["text"] == "certificate says Y"
    records = authority.divergence(claims)
    assert records and records[0]["loses_to"] == "certified"


def test_unknown_layer_is_refused():
    with pytest.raises(authority.UnknownLayer):
        authority.winner([{"layer": "vibes", "text": "x"}])


def test_formulas_are_versioned_and_compute_real_numbers():
    nights = formulas.evaluate(
        "stay_nights", {"check_in_date": "2026-09-03", "check_out_date": "2026-09-06"}
    )
    assert nights["result"] == 3.0
    charge = formulas.evaluate("room_charge", {"nights": 3, "nightly_rate": 145.0})
    assert charge["result"] == 435.0
    occupancy = formulas.evaluate("occupancy_percent", {"arrivals_count": 20})
    assert occupancy["result"] == 50.0
    with pytest.raises(formulas.UnknownFormula):
        formulas.evaluate("free_money", {})


def test_corpus_is_tenant_scoped_and_answers_carry_labels(client, monkeypatch):
    monkeypatch.setenv("TENANT_TOKENS", "token-a:tenant-a,token-b:tenant-b")
    doc = client.post(
        "/v1/corpus/documents",
        json={
            "title": "Late arrival policy",
            "body": "A guest arriving after midnight is checked in and housekeeping is notified.",
            "certified": True,
        },
        headers={"Authorization": "Bearer token-a"},
    )
    assert doc.status_code == 200, doc.text[:200]
    tenant_a = client.get("/v1/corpus/documents", headers={"Authorization": "Bearer token-a"})
    tenant_b = client.get("/v1/corpus/documents", headers={"Authorization": "Bearer token-b"})
    assert tenant_a.json()["total"] >= 1
    assert tenant_b.json()["total"] == 0

    answer = client.get(
        "/v1/answers?q=late arrival housekeeping",
        headers={"Authorization": "Bearer token-a"},
    )
    assert answer.status_code == 200
    body = answer.json()
    assert body["ok"] is True
    assert body["winner"]["layer"] == "certified"
    assert body["labels"] and body["labels"][0]["rank"] == 1
    assert body["network"] == "none"

    empty = client.get(
        "/v1/answers?q=late arrival housekeeping",
        headers={"Authorization": "Bearer token-b"},
    )
    assert empty.json()["winner"] is None


def test_a_tenant_header_that_disagrees_with_the_token_is_refused(client, monkeypatch):
    monkeypatch.setenv("TENANT_TOKENS", "token-a:tenant-a")
    resp = client.get(
        "/v1/corpus/documents",
        headers={"Authorization": "Bearer token-a", "X-Tenant": "tenant-b"},
    )
    assert resp.status_code == 403


def test_llm_status_never_claims_a_provider():
    body = llm.status()
    assert body["engine"] == "offline-deterministic"
    assert body["provider"] == "none"
    assert body["network"] == "none"
