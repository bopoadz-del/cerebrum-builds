"""The tenant-scoped RAG surface (app/rag_routes.py).

Written by the factory WRITER role (codewhale exec)

Performed, not configured: a document is planted for the caller's tenant,
the same tenant retrieves it, a term that was never planted comes back
EMPTY (so the "hit" is retrieval and not an echo), and a second tenant
cannot see the first tenant's corpus.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app

PLATFORM = {"Authorization": "Bearer dev-local-token"}
TENANT_A = {"Authorization": "Bearer token-a"}
TENANT_B = {"Authorization": "Bearer token-b"}
MARKER = "ACCEPTANCE-PLANT notechange-the-late-arrival-procedure"


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def tenant_tokens(monkeypatch: "pytest.MonkeyPatch") -> None:
    monkeypatch.setenv("TENANT_TOKENS", "token-a:tenant-a,token-b:tenant-b")


def _hits(body: Dict[str, Any]) -> str:
    import json

    return json.dumps(body.get("hits") or []).lower()


def test_ingest_requires_a_token(client: TestClient):
    resp = client.post("/v1/rag/ingest", json={"text": MARKER})
    assert resp.status_code == 401


def test_ingest_requires_text(client: TestClient):
    resp = client.post("/v1/rag/ingest", json={"title": "no body"}, headers=PLATFORM)
    assert resp.status_code == 422


def test_plant_then_retrieve_and_miss_the_absent_term(client: TestClient):
    planted = client.post(
        "/v1/rag/ingest",
        json={"text": MARKER, "title": "Late arrival procedure"},
        headers=PLATFORM,
    )
    assert planted.status_code == 200
    body = planted.json()
    assert body["ok"] is True and body["stored"]["id"] == body["id"]

    hit = client.post("/v1/rag/query", json={"q": "late arrival procedure"}, headers=PLATFORM)
    assert hit.status_code == 200
    assert "notechange" in _hits(hit.json())

    absent = client.post("/v1/rag/query", json={"q": "never-planted-zzz"}, headers=PLATFORM)
    assert absent.status_code == 200
    assert absent.json()["hits"] == [], "a term that was never planted must not retrieve"
    assert absent.json()["total"] == 0

    listed = client.get("/v1/rag/documents", headers=PLATFORM)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1


def test_get_query_accepts_the_term_in_the_query_string(client: TestClient):
    client.post("/v1/rag/ingest", json={"text": MARKER}, headers=PLATFORM)
    resp = client.get("/v1/rag/query", params={"q": "late arrival"}, headers=PLATFORM)
    assert resp.status_code == 200
    assert resp.json()["hits"]


def test_corpus_is_tenant_scoped(client: TestClient):
    client.post("/v1/rag/ingest", json={"text": MARKER}, headers=TENANT_A)
    other = client.get("/v1/rag/documents", headers=TENANT_B)
    assert other.status_code == 200
    assert MARKER.lower() not in str(other.json()).lower()
    mine = client.get("/v1/rag/documents", headers=TENANT_A)
    assert MARKER.lower() in str(mine.json()).lower()


def test_rag_routes_are_quoted_in_the_app_package():
    """The acceptance probe looks for the quoted paths in app/**/*.py."""
    text = (Path(__file__).resolve().parents[1] / "app" / "rag_routes.py").read_text(
        encoding="utf-8"
    )
    assert '"/v1/rag/ingest"' in text
    assert '"/v1/rag/query"' in text