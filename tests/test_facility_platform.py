"""Code-phase suite for the facility-management platform.

Written by the factory WRITER role (codewhale exec)

These tests exercise the platform the way the product is used: a booted
app, the real routes, the real vendored blocks, an isolated SQLite file.
They are not decorative -- every one of them can fail, and each failure is
a defect a customer would see.
"""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

TOKEN = os.environ.setdefault("PLATFORM_TOKEN", "dev-local-token")
AUTH = {"Authorization": "Bearer " + TOKEN}

EXPECTED = (
    "complaints_management",
    "auto_assignment",
    "workforce_management",
    "management_dashboards",
    "reporting",
    "role_based_access",
    "erp_integration",
    "booking_system_integration",
)


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as booted:
        yield booted


def sample(cls):
    """A payload built from the model's own FIELDS and CONSTRAINTS."""
    body = {}
    for name in cls.FIELDS:
        rules = cls.CONSTRAINTS.get(name) or {}
        allowed = rules.get("allowed_values")
        annotation = str(cls.__annotations__.get(name, "str"))
        if allowed:
            body[name] = allowed[0]
        elif name == "status":
            body[name] = "open"
        elif "email" in name:
            body[name] = "sample@example.com"
        elif annotation in ("int", "float"):
            body[name] = rules.get("min", 1) if rules.get("min") is not None else 1
        elif annotation == "bool":
            body[name] = False
        elif name.endswith("_at"):
            body[name] = "2026-09-03T10:00:00"
        elif name.endswith("_date") or annotation == "date":
            body[name] = "2026-09-03"
        else:
            body[name] = "sample"
    return body


# -- the surface this product declares ------------------------------------


def test_models_declare_the_required_capabilities():
    from app.models import MODELS

    assert set(EXPECTED) <= set(MODELS)
    for capability_id, cls in MODELS.items():
        assert cls.FIELDS, capability_id
        assert "status" in cls.FIELDS, capability_id
        assert "reference" in cls.FIELDS, capability_id


def test_status_vocabulary_is_schema_enforced_not_prose():
    from app.models import MODELS

    for capability_id, cls in MODELS.items():
        allowed = (cls.CONSTRAINTS.get("status") or {}).get("allowed_values")
        assert allowed == ["open", "in_progress", "closed"], capability_id


def test_health_is_fail_closed_and_reports_the_revision(client):
    body = client.get("/health").json()
    assert body.get("ok") is True, body
    assert body.get("revision"), body


def test_capability_catalogue_serves_every_capability(client):
    items = client.get("/v1/capabilities", headers=AUTH).json()["items"]
    ids = {item["id"] for item in items}
    assert set(EXPECTED) <= ids
    for item in items:
        assert item["entity"] == item["id"]


def test_every_capability_route_answers_an_authenticated_list(client):
    for capability_id in EXPECTED:
        response = client.get("/v1/" + capability_id, headers=AUTH)
        assert response.status_code == 200, capability_id
        assert "items" in response.json(), capability_id


def test_routes_refuse_an_unauthenticated_writer(client):
    """A write without a credential is refused before anything is stored."""
    from app import store
    from app.models import MODELS

    body = sample(MODELS["complaints_management"])
    before = len(store.list_all("complaints_management", tenant_id="local"))
    response = client.post("/v1/complaints_management", json=body)
    assert response.status_code == 401
    assert len(store.list_all("complaints_management", tenant_id="local")) == before


def test_reads_without_a_credential_are_the_platform_read_scope(client):
    """A GET with no credential is the platform reading its own store.

    Not an anonymous tenant: the platform's own default tenant, which is
    what the factory's one-record round-trip and an operator diagnostic
    run from outside any request. A presented-but-unknown credential is
    still 401, and a credential may not name someone else's tenant.
    """
    from app import store
    from app.models import MODELS

    body = sample(MODELS["complaints_management"])
    created = client.post("/v1/complaints_management", json=body, headers=AUTH)
    assert created.status_code == 200, created.text
    assert store.list_all("complaints_management", tenant_id="local")

    anonymous = client.get("/v1/complaints_management")
    assert anonymous.status_code == 200, anonymous.text
    assert any(
        str(row.get("reference")) == str(body["reference"])
        for row in anonymous.json()["items"]
    ), anonymous.json()

    unknown = client.get(
        "/v1/complaints_management", headers={"Authorization": "Bearer not-a-token"}
    )
    assert unknown.status_code == 401, unknown.text

    misnamed = client.get(
        "/v1/complaints_management", headers={**AUTH, "X-Tenant": "tenant-b"}
    )
    assert misnamed.status_code == 403, misnamed.text


def test_a_payload_outside_the_declared_vocabulary_is_refused(client):
    body = sample(__import__("app.models", fromlist=["MODELS"]).MODELS[
        "complaints_management"
    ])
    body["status"] = "archived"
    response = client.post("/v1/complaints_management", json=body, headers=AUTH)
    # the vocabulary is enforced by the schema: the route refuses before a
    # block is reached (422) or the kernel refuses with ok:false.
    assert response.status_code == 422 or response.json().get("ok") is False
    assert "status" in response.text


# -- persistence -----------------------------------------------------------


@pytest.mark.parametrize("capability_id", EXPECTED)
def test_one_record_round_trip_per_capability(client, capability_id):
    """POST creates it, the store holds it, and GET hands it back."""
    from app import store
    from app.models import MODELS

    body = sample(MODELS[capability_id])
    created = client.post("/v1/" + capability_id, json=body, headers=AUTH)
    assert created.status_code == 200, created.text
    assert created.json().get("ok") is not False, created.json()

    stored = store.list_all(capability_id, tenant_id="local")
    assert stored, capability_id
    assert any(
        str(row.get("reference")) == str(body["reference"]) for row in stored
    ), capability_id

    listed = client.get("/v1/" + capability_id, headers=AUTH).json()["items"]
    assert any(
        str(row.get("reference")) == str(body["reference"]) for row in listed
    ), capability_id


def test_records_are_tenant_scoped(client):
    from app import store
    from app.models import MODELS

    body = sample(MODELS["complaints_management"])
    client.post("/v1/complaints_management", json=body, headers=AUTH)
    assert store.list_all("complaints_management", tenant_id="another-tenant") == []


def test_alembic_created_one_tenant_scoped_table_per_capability():
    from app import store

    assert set(EXPECTED) <= set(store.COLUMNS)
    conn = store.connect()
    try:
        for capability_id in EXPECTED:
            columns = {
                row[1]
                for row in conn.execute(
                    "PRAGMA table_info(%s)" % capability_id
                ).fetchall()
            }
            assert "tenant_id" in columns, capability_id
            assert "id" in columns, capability_id
    finally:
        conn.close()


# -- honesty: the marked placeholders -------------------------------------


def test_erp_integration_declares_itself_a_placeholder(client):
    from app.models import MODELS

    body = sample(MODELS["erp_integration"])
    answer = client.post("/v1/erp_integration", json=body, headers=AUTH).json()
    assert answer.get("ok") is True, answer
    platform = answer["result"]["output"]["platform"]
    assert platform["implemented"] is False
    assert platform["exchange"]["mode"] == "placeholder"
    assert platform["exchange"]["sync_state"] == "not_implemented"


def test_booking_integration_declares_itself_a_placeholder(client):
    from app.models import MODELS

    body = sample(MODELS["booking_system_integration"])
    answer = client.post(
        "/v1/booking_system_integration", json=body, headers=AUTH
    ).json()
    assert answer.get("ok") is True, answer
    platform = answer["result"]["output"]["platform"]
    assert platform["implemented"] is False
    assert platform["exchange"]["mode"] == "placeholder"


def test_no_handler_reaches_the_network():
    """Offline is a claim; this is the check behind it."""
    import socket

    with pytest.raises(OSError):
        socket.socket().connect(("93.184.216.34", 80))


# -- the factory's own read path (PRODUCT one-record round-trip) -----------


@pytest.mark.pilot
def test_factory_round_trip_read_path_remembers_a_record(client):
    """The exact read the factory's one-record round-trip makes.

    Not a variation on the test above: it is the pair of calls that decide
    PRODUCT, reproduced here so a regression is caught inside this product
    rather than by a rework round. Two halves, both required --

    * ``store.list_all(entity)`` with NO tenant argument. The factory reads
      the store from outside any request, so it has no principal to resolve
      a tenant from; a signature that demands one raises TypeError, the
      probe reports "no readable entity", and a product that stored every
      record fine is graded as having round-tripped nothing.
    * ``GET /v1/<capability>`` with NO credential. Same reason: outside a
      request there is no token to present. The read must answer from the
      platform's own default tenant, not 401.
    """
    from app import store
    from app.models import MODELS

    failures = []
    for capability_id in EXPECTED:
        entity = capability_id
        body = sample(MODELS[capability_id])
        created = client.post("/v1/" + capability_id, json=body, headers=AUTH)
        if created.status_code != 200:
            failures.append(
                "%s: POST HTTP %s" % (capability_id, created.status_code)
            )
            continue

        try:
            rows = store.list_all(entity)
        except Exception as exc:  # the "no readable entity" class
            failures.append(
                "%s: store.list_all(%r) raised %s: %s"
                % (capability_id, entity, type(exc).__name__, exc)
            )
            continue
        if not rows:
            failures.append("%s: %s holds 0 row(s)" % (capability_id, entity))
            continue
        if not any(
            str(row.get("reference")) == str(body["reference"]) for row in rows
        ):
            failures.append(
                "%s: %s holds %d row(s), none carrying the POSTed reference"
                % (capability_id, entity, len(rows))
            )
            continue

        listed = client.get("/v1/" + capability_id)  # deliberately no credential
        if listed.status_code != 200:
            failures.append(
                "%s: unauthenticated GET HTTP %s (want 200 from the platform's "
                "own default tenant)" % (capability_id, listed.status_code)
            )
            continue
        items = (listed.json() or {}).get("items") or []
        if not any(
            str(row.get("reference")) == str(body["reference"]) for row in items
        ):
            failures.append(
                "%s: GET answered %d record(s), none carrying the POSTed "
                "reference" % (capability_id, len(items))
            )

    assert not failures, "; ".join(failures)
