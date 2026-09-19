"""PRODUCT pilot suite: the product remembers one record it was given.

Written by the factory WRITER role (codewhale exec)

Run post-boot against the booted product (``pytest -m pilot``). Each test POSTs
a schema-sample payload, re-reads the capability's own store entity, and then
makes the GET a buyer makes.
"""

from __future__ import annotations

import pytest

from app import store
from app.models import MODELS, ENTITIES
from tests.helpers import AUTH, client, sample_payload

pytestmark = pytest.mark.pilot

CAPABILITY_IDS = sorted(MODELS)


@pytest.mark.parametrize("capability_id", CAPABILITY_IDS)
def test_capability_remembers_one_record(capability_id):
    body = sample_payload(capability_id)
    entity = ENTITIES[capability_id]
    with client() as c:
        created = c.post("/v1/" + capability_id, json=body, headers=AUTH)
        assert created.status_code == 200, created.text
        assert created.json().get("ok") is not False, created.json().get("error")

        rows = store.list_all(entity, tenant_id="local")
        assert rows, f"{entity} holds no row after a successful POST"
        assert any(str(row.get("reference")) == str(body["reference"]) for row in rows)

        listed = c.get("/v1/" + capability_id)
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert items and any(
            str(row.get("reference")) == str(body["reference"]) for row in items
        )


@pytest.mark.parametrize("capability_id", CAPABILITY_IDS)
def test_persisted_row_uses_the_capability_entity(capability_id):
    assert ENTITIES[capability_id] == capability_id
    assert capability_id in store.COLUMNS
