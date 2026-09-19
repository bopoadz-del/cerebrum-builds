"""Kernel contract: registry, lifecycle actions, isolation and provenance."""

from __future__ import annotations

import pytest

from app.cerebrum_product_kernel import isolation
from app.cerebrum_product_kernel.contract import CAPABILITIES, execute_action, contract_for
from app.cerebrum_product_kernel.formulas import definitions, names
from app.cerebrum_product_kernel.provenance import for_record
from tests.helpers import sample_payload


def test_registry_carries_every_capability():
    from app.models import MODELS

    assert sorted(CAPABILITIES) == sorted(MODELS)
    for capability_id, contract in CAPABILITIES.items():
        assert contract["entity"] == capability_id
        assert contract["status_vocabulary"] == ["open", "in_progress", "closed"]
        assert contract["blocks"]


def test_contract_for_unknown_capability_is_none():
    assert contract_for("not_a_capability") is None


def test_kernel_lifecycle_actions():
    capability_id = "management_reporting_dashboard"
    created = execute_action(capability_id, "create", sample_payload(capability_id))
    assert created["ok"] is True, created.get("error")
    record_id = created["record"]["id"]
    assert execute_action(capability_id, "read", record_id=record_id)["ok"] is True
    listed = execute_action(capability_id, "list")
    assert any(row["id"] == record_id for row in listed["items"])
    update_body = sample_payload(capability_id)
    update_body["reference"] = "updated"
    update_body["status"] = "in_progress"
    updated = execute_action(
        capability_id, "update", update_body, record_id=record_id,
    )
    assert updated["ok"] is True
    assert execute_action(capability_id, "read", record_id=record_id)["record"]["reference"] == "updated"
    assert execute_action(capability_id, "delete", record_id=record_id)["deleted"] is True


def test_kernel_refuses_unknown_action():
    result = execute_action("management_reporting_dashboard", "publish")
    assert result["ok"] is False
    assert "Unknown action" in result["error"]


def test_isolation_guards():
    assert isolation.assert_single_persistence_root()
    isolation.assert_entity_migrated("stock_inventory_management")
    with pytest.raises(isolation.IsolationError):
        isolation.assert_entity_migrated("no_such_entity")


def test_formula_definitions_are_versioned_data():
    body = definitions()
    assert body["version"] == "formulas.v1"
    assert "delivery_cost" in names()


def test_provenance_digest_is_stable():
    first = for_record("stock_inventory_management", "stock_inventory_management",
                       ["database"], {"reference": "a"})
    second = for_record("stock_inventory_management", "stock_inventory_management",
                        ["database"], {"reference": "a"})
    assert first.record_digest == second.record_digest
