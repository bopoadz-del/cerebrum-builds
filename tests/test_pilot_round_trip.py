"""PRODUCT pilot suite: one record per capability survives a POST and a GET.

Written by the factory WRITER role (codewhale exec).

Marked ``pilot``: this is the Store-backed execute-all the PRODUCT gate runs
against the booted product, not the code-phase suite. Every capability is
posted with a payload built from its own model, then re-read from the store,
from ``GET /v1/{capability}`` and from ``GET /v1/{capability}/{id}`` —
"remembered a record it was given", measured rather than asserted.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app
from app.models import MODELS

CLIENT = TestClient(app)
AUTH = {
    "Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")
}

CAPABILITY_IDS = sorted(MODELS)


def sample_payload(capability_id: str) -> dict:
    """A valid instance of the capability, built from its own model."""
    cls = MODELS[capability_id]
    constraints = getattr(cls, "CONSTRAINTS", {}) or {}
    out: dict = {}
    for name in cls.FIELDS:
        rules = constraints.get(name) or {}
        if rules.get("allowed_values"):
            out[name] = rules["allowed_values"][0]
        elif rules.get("min") is not None:
            out[name] = rules["min"]
        elif str(rules.get("format") or "") == "date" or name.endswith("_date"):
            out[name] = "2026-09-03"
        elif str(rules.get("format") or "") == "datetime" or name.endswith("_at"):
            out[name] = "2026-09-03T10:00:00"
        elif "email" in name:
            out[name] = "guest@example.com"
        else:
            out[name] = "sample"
    return out


def _listed(payload: object) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict) or payload.get("ok") is False:
        return []
    for key in ("items", "records", "results", "data", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


@pytest.mark.pilot
def test_health_is_fail_closed_and_green():
    resp = CLIENT.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok" and body["ok"] is True
    names = {item["name"] for item in body["checks"]}
    assert {"process", "persistent_disk", "database", "migrations"} <= names


@pytest.mark.pilot
@pytest.mark.parametrize("capability_id", CAPABILITY_IDS)
def test_one_record_round_trip(capability_id: str):
    payload = sample_payload(capability_id)
    payload["reference"] = "pilot-" + capability_id
    resp = CLIENT.post(f"/v1/{capability_id}", json=payload, headers=AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("ok") is not False, body
    stored = body.get("stored") or {}
    record_id = stored.get("id")
    assert record_id is not None, body

    rows = store.list_all(capability_id)
    assert any(row.get("reference") == payload["reference"] for row in rows), (
        f"{capability_id} did not remember the record it was given"
    )

    listed = CLIENT.get(f"/v1/{capability_id}")
    assert listed.status_code == 200, listed.text
    assert any(
        row.get("reference") == payload["reference"] for row in _listed(listed.json())
    ), f"{capability_id} accepted a record but its list does not return it"

    got = CLIENT.get(f"/v1/{capability_id}/{record_id}")
    assert got.status_code == 200, got.text
    record = got.json()
    assert record["reference"] == payload["reference"]
    assert record["status"] == payload["status"]


@pytest.mark.pilot
@pytest.mark.parametrize("capability_id", CAPABILITY_IDS)
def test_persisted_record_survives_reconnect(capability_id: str):
    """The record is on disk, not in a connection-scoped cache."""
    payload = sample_payload(capability_id)
    payload["reference"] = "durable-" + capability_id
    resp = CLIENT.post(f"/v1/{capability_id}", json=payload, headers=AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("ok") is not False, body
    record_id = (body.get("stored") or {}).get("id")
    assert record_id is not None, body
    from app.store import get as _get

    fetched = _get(capability_id, record_id)
    assert fetched is not None
    assert fetched["reference"] == payload["reference"]


@pytest.mark.pilot
def test_rag_ingest_query_round_trip():
    """POST /v1/rag/ingest then GET /v1/rag/query answers with a citation."""
    text = (
        "RetailOS stock policy: a SKU below its reorder point is replenished "
        "before the next trading week."
    )
    ingested = CLIENT.post(
        "/v1/rag/ingest",
        json={"text": text, "doc_id": "stock-policy", "collection": "retail_corpus"},
        headers=AUTH,
    )
    assert ingested.status_code == 200, ingested.text
    assert ingested.json()["ok"] is True

    queried = CLIENT.get(
        "/v1/rag/query", params={"q": "reorder point replenished"}, headers=AUTH
    )
    assert queried.status_code == 200, queried.text
    body = queried.json()
    assert body["ok"] is True
    assert body["hits"], "the ingested document was not retrievable"


@pytest.mark.pilot
def test_unknown_query_field_is_refused_not_ignored():
    resp = CLIENT.get("/v1/inventory_management", params={"staus": "open"})
    assert resp.status_code == 200
    assert resp.json().get("ok") is False
