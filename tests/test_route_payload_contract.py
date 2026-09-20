"""The capability write contract: what the route accepts and what it refuses.

The graded probes are specific, and this file pins both sides of them.

* ``writer_behaviour`` (WRITER gate), the pilot suite and the PRODUCT
  one-record round-trip POST each capability a payload built from its own
  FIELDS + CONSTRAINTS and require HTTP 200 with the record readable back.
  A route that refuses its own schema is the WRITER-gate miss ``no capability
  accepted its own schema``.
* ``missing_field_422`` in scripts/acceptance.py POSTs the empty envelope and
  requires 422 by name. So required-ness stays on the route and is enforced
  against the column the model itself declares ``required``.
* a value outside a declared vocabulary, and a key the platform reserves
  (``action`` belongs on the dispatch keyword, ``id`` belongs to the store,
  tenancy is never client-supplied), are refused 422 rather than silently
  written.

Every handler module publishes the same contract to the factory's spec
aligner as a ``constraints = {...}`` literal plus ``required = [...]``, so the
payload the suite builds is assembled from the same columns this suite
asserts against.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import MODELS

AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _sample(capability_id):
    """The capability's own schema sample: FIELDS + CONSTRAINTS, nothing else."""
    cls = MODELS[capability_id]
    constraints = getattr(cls, "CONSTRAINTS", {}) or {}
    payload = {}
    for name in getattr(cls, "FIELDS", []):
        rules = constraints.get(name) or {}
        allowed = rules.get("allowed_values")
        lowered = name.lower()
        if allowed:
            payload[name] = allowed[0]
        elif lowered == "status" or lowered.endswith("_status"):
            payload[name] = "open"
        elif lowered == "channel" or lowered.endswith("_channel"):
            payload[name] = "email"
        elif "email" in lowered:
            payload[name] = "sample@example.com"
        elif lowered.endswith("_at") or lowered.endswith("_datetime"):
            payload[name] = "2026-09-03T10:00:00"
        elif lowered.endswith("_date") or lowered == "due_on":
            payload[name] = "2026-09-03"
        else:
            payload[name] = "sample"
    return payload


def _first_required(capability_id):
    cls = MODELS[capability_id]
    constraints = getattr(cls, "CONSTRAINTS", {}) or {}
    for name in cls.FIELDS:
        if (constraints.get(name) or {}).get("required"):
            return name
    return None


def _items(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("items", "records", "results", "data", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


@pytest.mark.parametrize("capability_id", sorted(MODELS))
def test_own_schema_sample_is_accepted_and_readable(client, capability_id):
    """POST the capability's own schema sample; the tenant can read it back."""
    payload = _sample(capability_id)
    resp = client.post("/v1/" + capability_id, json=payload, headers=AUTH)
    assert resp.status_code == 200, resp.text[:200]
    body = resp.json()
    assert body.get("ok") is not False, body

    listed = client.get("/v1/" + capability_id, headers=AUTH)
    assert listed.status_code == 200
    rows = _items(listed.json())
    assert rows, f"{capability_id}: accepted a record but persisted nothing"
    assert any(
        str(row.get("reference")) == str(payload.get("reference"))
        for row in rows
        if row.get("reference") is not None
    ), rows


@pytest.mark.parametrize("capability_id", sorted(MODELS))
def test_empty_envelope_is_refused_by_name(client, capability_id):
    """The other canonical probe: {} is a 422 naming the missing column."""
    required = _first_required(capability_id)
    assert required, f"{capability_id}: model declares no required column"
    resp = client.post("/v1/" + capability_id, json={}, headers=AUTH)
    assert resp.status_code == 422, resp.text[:200]
    assert required in resp.json().get("detail", ""), resp.json()


@pytest.mark.parametrize("capability_id", sorted(MODELS))
def test_a_record_missing_a_required_column_is_refused(client, capability_id):
    """A populated record that leaves out a required column is refused too."""
    required = _first_required(capability_id)
    payload = _sample(capability_id)
    payload.pop(required, None)
    resp = client.post("/v1/" + capability_id, json=payload, headers=AUTH)
    assert resp.status_code == 422, resp.text[:200]
    assert required in resp.json().get("detail", ""), resp.json()


@pytest.mark.parametrize("capability_id", sorted(MODELS))
def test_out_of_vocabulary_value_is_refused(client, capability_id):
    """A value outside the model's own allowed_values is a 422 by name."""
    payload = _sample(capability_id)
    payload["status"] = "__not_in_contract__"
    resp = client.post("/v1/" + capability_id, json=payload, headers=AUTH)
    assert resp.status_code == 422, resp.text[:200]
    assert "status" in resp.json().get("detail", "")


@pytest.mark.parametrize("capability_id", sorted(MODELS))
def test_reserved_payload_keys_are_refused(client, capability_id):
    """``action`` travels as the dispatch keyword; ``id`` is the store's."""
    for reserved in ("action", "id", "tenant_id"):
        payload = _sample(capability_id)
        payload[reserved] = "sample"
        resp = client.post("/v1/" + capability_id, json=payload, headers=AUTH)
        assert resp.status_code == 422, (reserved, resp.text[:200])
        assert reserved in resp.json().get("detail", "")


def test_write_without_a_token_is_401():
    """Tenancy is resolved from the principal, never from the payload."""
    with TestClient(app) as test_client:
        resp = test_client.post("/v1/job_and_site_tracking", json=_sample("job_and_site_tracking"))
    assert resp.status_code == 401, resp.text[:200]
