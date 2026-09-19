"""Pilot: the local retrieval surface plants a document and finds it.

Offline by construction — the index is lexical (token overlap, inverse
document frequency) inside the platform sqlite file. This suite asserts the
two halves that matter: a planted paragraph is retrievable by a word from
it, and a term that was never planted returns nothing (a query that echoes
its own request is not retrieval).
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}


@pytest.mark.pilot
def test_rag_ingest_then_query_round_trips():
    nonce = uuid.uuid4().hex[:12]
    marker = f"recall interval guidance {nonce} for the hygiene schedule"
    planted = client.post(
        "/v1/rag/ingest",
        json={"text": marker, "source": "clinic-sop"},
        headers=AUTH,
    )
    assert planted.status_code == 200, planted.text[:200]
    assert planted.json()["ingested"] >= 1

    found = client.post("/v1/rag/query", json={"q": marker}, headers=AUTH)
    assert found.status_code == 200, found.text[:200]
    body = found.json()
    assert body["count"] >= 1
    assert nonce in str(body["hits"]), body

    absent = uuid.uuid4().hex[:12]
    miss = client.post("/v1/rag/query", json={"q": absent}, headers=AUTH)
    assert miss.status_code == 200
    assert miss.json()["hits"] == [], miss.json()


@pytest.mark.pilot
def test_rag_query_is_tenant_scoped():
    nonce = uuid.uuid4().hex[:12]
    marker = f"tenant private note {nonce} about a treatment plan"
    planted = client.post(
        "/v1/rag/ingest",
        json={"text": marker},
        headers={"Authorization": "Bearer token-a"},
    )
    assert planted.status_code == 200, planted.text[:200]

    other = client.post(
        "/v1/rag/query",
        json={"q": marker},
        headers={"Authorization": "Bearer token-b"},
    )
    assert other.status_code == 200
    assert other.json()["hits"] == [], other.json()


def test_rag_query_answers_without_principal_for_reads():
    """The read path resolves to the platform tenant; it never 500s."""
    resp = client.get("/v1/rag/query", params={"q": "nothing planted"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_rag_ingest_requires_token():
    resp = client.post("/v1/rag/ingest", json={"text": "unauthenticated"})
    assert resp.status_code == 401
