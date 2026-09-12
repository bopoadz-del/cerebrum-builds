"""PRODUCT gate: schema-sample accept + one-record round-trip. pytest -m pilot."""

from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from app.schema import REQUIRED_CAPABILITY_IDS, SPECS

pytestmark = pytest.mark.pilot


def _sample_payload(capability_id: str) -> Dict[str, Any]:
    spec = SPECS[capability_id]
    body: Dict[str, Any] = {}
    for name, meta in spec["FIELDS"].items():
        constraints = spec["CONSTRAINTS"].get(name) or {}
        allowed = constraints.get("allowed_values")
        if allowed:
            body[name] = allowed[0]
        elif name == "status" or name.endswith("_status"):
            body[name] = "open"
        elif name == "channel" or name.endswith("_channel"):
            body[name] = "email"
        elif name.endswith("_at") or name.endswith("_datetime") or meta.get("type") == "datetime":
            body[name] = "2026-09-03T10:00:00"
        elif name.endswith("_date") or meta.get("type") == "date":
            body[name] = "2026-09-03"
        elif name.endswith("_time") or meta.get("type") == "time":
            body[name] = "10:00:00"
        elif "email" in name:
            body[name] = "guest@example.com"
        elif meta.get("type") in {"int", "integer", "float", "number"}:
            body[name] = constraints.get("min", 1)
        elif meta.get("type") == "bool":
            body[name] = False
        else:
            body[name] = "sample"
    return body


def test_every_capability_route_accepts_payload(client: TestClient) -> None:
    for capability_id in REQUIRED_CAPABILITY_IDS:
        payload = _sample_payload(capability_id)
        response = client.post(f"/v1/{capability_id}", json=payload)
        assert response.status_code == 200, capability_id
        body = response.json()
        assert body.get("ok") is not False, f"{capability_id} rejected a payload built from its own schema: {body}"


def test_one_record_round_trip_per_capability(client: TestClient) -> None:
    from app.store import list_all

    for capability_id in REQUIRED_CAPABILITY_IDS:
        payload = _sample_payload(capability_id)
        post = client.post(f"/v1/{capability_id}", json=payload)
        assert post.status_code == 200, capability_id
        assert post.json().get("ok") is not False, capability_id
        entity = SPECS[capability_id]["entity"]
        stored = list_all(entity)
        assert stored, f"{capability_id} did not remember a record they were given"
        got = client.get(f"/v1/{capability_id}")
        assert got.status_code == 200
        records = got.json().get("records") or []
        assert records, f"{capability_id} GET did not return the persisted record"
        assert any(row.get("reference") == payload["reference"] for row in records)


def test_health_and_ui(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    ui = client.get("/")
    assert ui.status_code == 200
    assert "Product Platform" in ui.text


def test_writes_require_token(anon_client: TestClient) -> None:
    denied_core = anon_client.post(
        "/v1/product_core", json={"reference": "sample", "status": "open"}
    )
    denied_audit = anon_client.post(
        "/v1/audit", json={"reference": "sample", "status": "open"}
    )
    denied_ingest = anon_client.post(
        "/v1/rag/ingest",
        json={"layer": 1, "doc_id": "denied", "title": "x", "text": "budget vs actual"},
    )
    denied_steward = anon_client.post(
        "/v1/steward/rag/ingest",
        json={"layer": 1, "doc_id": "denied", "title": "x", "text": "budget vs actual"},
    )
    assert denied_core.status_code == 401
    assert denied_audit.status_code == 401
    assert denied_ingest.status_code == 401
    assert denied_steward.status_code == 401


def test_audit_ignores_forged_client_actor(client: TestClient) -> None:
    payload = _sample_payload("audit")
    payload["actor"] = "forged-admin"
    payload["user_id"] = "attacker"
    payload["principal"] = "spoofed"
    response = client.post("/v1/audit", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body.get("ok") is not False, body
    assert body.get("actor") == "operator"
    assert body.get("actor_role") == "admin"
    record = body.get("record") or {}
    assert record.get("actor") == "operator"
    assert record.get("actor_role") == "admin"
    assert record.get("user_id") != "attacker"
    claimed = record.get("claimed_actor") or {}
    assert claimed.get("actor") == "forged-admin"
    blocks = (body.get("blocks") or {}).get("audit") or {}
    inner = blocks.get("result") if isinstance(blocks, dict) else {}
    if isinstance(inner, dict) and inner.get("user_id"):
        assert inner.get("user_id") == "operator"
