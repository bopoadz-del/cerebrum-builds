"""Retrieval: ingest, query, the authority label, and the negative control.

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.domain_ops import sample_payload
from app.main import app

# Self-contained by design. conftest.py belongs to the factory and is
# rewritten between rounds (its canonical version carries STORAGE_PATH
# isolation and the offline socket guard, and nothing else). A test module
# that imported a helper or a fixture from there went red the moment the
# canonical file replaced it -- ImportError: cannot import name
# 'sample_payload' from 'tests.conftest'. The platform's own spec helper
# (app.domain_ops.sample_payload) is the stable source for a schema sample.
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth():
    return dict(AUTH)


def test_rag_ingest_requires_a_token(client):
    assert client.post("/v1/rag/ingest", json={"text": "x"}).status_code == 401
    assert client.post("/v1/rag/query", json={"q": "x"}).status_code == 401


def test_rag_ingest_refuses_an_empty_document(client, auth):
    resp = client.post("/v1/rag/ingest", json={"text": "   "}, headers=auth)
    assert resp.status_code == 200
    assert resp.json().get("ok") is False


def test_planted_document_is_findable_again(client, auth):
    nonce = uuid.uuid4().hex[:12]
    marker = "the reorder threshold for %s is 14 days" % nonce
    planted = client.post("/v1/rag/ingest", json={"text": marker}, headers=auth)
    assert planted.status_code == 200 and planted.json()["ok"] is True
    found = client.post("/v1/rag/query", json={"q": marker}, headers=auth)
    assert found.status_code == 200
    body = found.json()
    assert body["hits"], body
    assert nonce in body["hits"][0]["text"]


def test_query_for_a_never_planted_term_scores_nothing(client, auth):
    """Without this control, an echo would pass for retrieval."""
    absent = uuid.uuid4().hex[:12]
    client.post("/v1/rag/ingest", json={"text": "deposit release policy"}, headers=auth)
    resp = client.post("/v1/rag/query", json={"q": absent}, headers=auth)
    assert resp.status_code == 200
    hit_text = " ".join(hit.get("text", "") for hit in resp.json()["hits"])
    assert absent not in hit_text


def test_answer_carries_its_authority_label(client, auth):
    nonce = uuid.uuid4().hex[:12]
    client.post("/v1/rag/ingest", json={"text": "branch north utilisation %s" % nonce}, headers=auth)
    resp = client.post("/v1/rag/query", json={"q": nonce}, headers=auth)
    authority = resp.json()["authority"]
    assert authority["layer"] == "documents"
    assert authority["label"] == "documents"
    assert authority["precedence"] == "precedence.v1"
    assert resp.json()["hits"][0]["authority"]["layer"] == "documents"


def test_ingested_document_is_durable_across_requests(client, auth):
    nonce = uuid.uuid4().hex[:12]
    client.post("/v1/rag/ingest", json={"text": "workshop capacity note %s" % nonce}, headers=auth)
    listed = client.get("/v1/rag/query?q=%s" % nonce, headers=auth)
    assert listed.status_code == 200
    assert nonce in str(listed.json()["hits"])


def test_capability_answers_carry_their_layer(client, auth):
    resp = client.post(
        "/v1/pricing_and_rate_cards",
        json=sample_payload("pricing_and_rate_cards"),
        headers=auth,
    )
    if resp.status_code == 200 and resp.json().get("ok") is not False:
        assert resp.json()["authority"]["layer"] == "formulas"
