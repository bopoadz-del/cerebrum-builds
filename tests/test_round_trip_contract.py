"""One-record round trip: the contract the PRODUCT gate measures.

Written by the factory WRITER role (codewhale exec)

The factory's one-record round trip is exact and identical for every
product: POST a payload built from the capability's own FIELDS +
CONSTRAINTS, then re-read ``store.list_all(entity)`` (one argument — the
probe has no request principal) and an *unauthenticated*
``GET /v1/{capability}``. A record the platform accepted must still be
there when the reader is not the caller.

Two earlier miss shapes are pinned here so they cannot come back:

* ``no readable entity`` — ``store.list_all(entity)`` raised TypeError
  because the read required a tenant argument, so the probe judged
  nothing (a gate that judged nothing is not a pass).
* ``stored the record, then GET answered HTTP 401`` — the list route
  refused the probe's anonymous read, so the record existed and could
  not be seen.

The count moves by exactly one, so "some row happened to match" cannot
stand in for "the POST was remembered".

The tenancy rules the read path must NOT weaken are pinned too: a
credential that is presented still has to resolve, and no caller may
name its own tenant.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app
from tests.helpers import AUTH, entity_of, listed, samples, same

client = TestClient(app)


@pytest.mark.parametrize("capability_id", sorted(samples()))
def test_one_record_round_trips_for_every_capability(capability_id):
    """POST creates it; the store and an anonymous GET hand it back."""
    payload = samples()[capability_id]
    entity = entity_of(capability_id)
    before = len(store.list_all(entity))

    created = client.post("/v1/" + capability_id, json=payload, headers=AUTH)
    assert created.status_code == 200, created.text
    assert created.json().get("ok") is not False, created.text

    # The factory probe's read: one argument, no request principal.
    stored = store.list_all(entity)
    assert len(stored) == before + 1, (
        f"{capability_id}: POST reported success and {entity} grew by "
        f"{len(stored) - before} row(s)"
    )
    assert any(
        any(same(row.get(name), value) for name, value in payload.items())
        for row in stored
    ), f"{capability_id}: {entity} holds no row carrying a value the POST supplied"

    seen = client.get("/v1/" + capability_id)
    assert seen.status_code == 200, (
        f"{capability_id}: stored the record, then GET answered HTTP "
        f"{seen.status_code}"
    )
    records = listed(seen.json())
    assert records, f"{capability_id}: {entity} holds a row and GET answered none"
    assert any(
        any(same(row.get(name), value) for name, value in payload.items())
        for row in records
    ), f"{capability_id}: GET returned rows, none carrying a value the POST supplied"


def test_presented_credential_must_resolve_on_a_read():
    """An unknown token is 401 — never a silent anonymous read."""
    resp = client.get(
        "/v1/record_checkin", headers={"Authorization": "Bearer not-a-token"}
    )
    assert resp.status_code == 401, resp.text


def test_anonymous_read_may_not_name_its_own_tenant():
    """A read that presents no credential may not choose a tenant."""
    resp = client.get("/v1/record_checkin", headers={"X-Tenant": "tenant-b"})
    assert resp.status_code == 403, resp.text


def test_write_without_a_credential_is_refused():
    """The board may be read without a token; it may never be written."""
    resp = client.post("/v1/record_checkin", json=samples()["record_checkin"])
    assert resp.status_code == 401, resp.text


def test_item_read_is_tenant_scoped(monkeypatch):
    """A record written by one tenant is not readable by another."""
    monkeypatch.setenv("TENANT_TOKENS", "token-b:tenant-b")
    payload = samples()["record_checkin"]
    created = client.post("/v1/record_checkin", json=payload, headers=AUTH)
    assert created.status_code == 200, created.text
    record_id = int(created.json()["stored"]["id"])
    other = client.get(
        f"/v1/record_checkin/{record_id}",
        headers={"Authorization": "Bearer token-b"},
    )
    assert other.status_code == 404, other.text
