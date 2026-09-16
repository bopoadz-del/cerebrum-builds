"""RetailOS domain behaviour, through the handlers themselves.

Written by the factory WRITER role (codewhale exec).

These are the store's own rules, not shape checks: a stock count at or
below its reorder point flags replenishment, an order publish carries a
non-empty topic on the in-process mcp channel, an omnichannel sync names
its channel, and a compliance entry hashes its own evidence bundle.
"""

from __future__ import annotations

import pytest

STOCK = {
    "reference": "inv-1",
    "status": "open",
    "sku": "SKU-1",
    "product_name": "Espresso beans 1kg",
    "location": "main store",
    "quantity_on_hand": 4,
    "reorder_point": 10,
    "unit_cost": 12.5,
    "supplier_name": "Northfield Roasters",
    "category": "grocery",
    "movement_type": "count",
    "last_counted_date": "2026-09-03",
}

ORDER = {
    "reference": "ord-1",
    "status": "open",
    "order_number": "SO-1",
    "customer_name": "Ada Retail",
    "customer_email": "guest@example.com",
    "channel": "in_store",
    "order_total": 84.0,
    "item_count": 2,
    "payment_status": "paid",
    "fulfilment_status": "open",
    "order_date": "2026-09-03",
    "notes": "collect in store",
}

SYNC = {
    "reference": "sync-1",
    "status": "open",
    "integration_name": "marketplace-bridge",
    "channel": "marketplace",
    "external_order_id": "ext-1",
    "sync_direction": "inbound",
    "sync_status": "complete",
    "sku": "SKU-1",
    "quantity": 2,
    "sync_at": "2026-09-03T10:00:00",
    "marketplace": "shopfront",
    "notes": "",
}

AUDIT = {
    "reference": "audit-1",
    "status": "open",
    "control_id": "PCI-DSS-3.2",
    "regulation": "PCI-DSS",
    "event_type": "transaction_log",
    "actor": "operator",
    "action_taken": "logged",
    "evidence_ref": "ev-1",
    "file_path": "",
    "findings": "none",
    "occurred_at": "2026-09-03T10:00:00",
    "severity": "low",
}


def test_reorder_signal_reads_the_records_own_count():
    from app.actions import inventory_management as inv

    assert inv._reorder_needed(STOCK) is True
    restocked = dict(STOCK, quantity_on_hand=25)
    assert inv._reorder_needed(restocked) is False
    assert "SKU-1" in inv._stock_brief(STOCK)
    assert inv._block_input("database", STOCK)["table"] == inv.ENTITY


def test_every_declared_block_is_fed_from_the_record():
    from app.actions import inventory_management as inv

    for block_id in inv.BLOCK_IDS:
        assert isinstance(inv._block_input(block_id, STOCK), dict)


@pytest.mark.pilot
def test_order_publish_is_prepared_for_the_store_bus():
    from app.actions import sales_and_orders as sales

    event = sales._block_input("event_bus", ORDER)
    assert event["topic"], "an event with no topic is refused by the bus"
    assert event["channel"] == "mcp"
    assert isinstance(event["payload"], dict) and event["message"]
    steps = sales._block_input("workflow", ORDER)["steps"]
    bus_steps = [step for step in steps if step.get("block") == "event_bus"]
    assert bus_steps, "the workflow must carry the store event"
    for step in bus_steps:
        assert step["action"] == "publish"
        assert step["input"]["topic"] and step["input"]["channel"] == "mcp"


@pytest.mark.pilot
def test_omnichannel_sync_names_its_channel():
    from app.actions import omnichannel_integration as omni

    event = omni._block_input("event_bus", SYNC)
    assert event["topic"].endswith("marketplace")
    assert event["payload"]["integration_name"] == "marketplace-bridge"
    steps = omni._block_input("workflow", SYNC)["steps"]
    assert steps[0]["block"] == "event_bus"
    assert steps[0]["action"] == "publish"


@pytest.mark.pilot
def test_compliance_evidence_is_hashed_and_verifiable(tmp_path, monkeypatch):
    from app.actions import compliance_and_audit as audit

    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    hasher = audit._block_input("file_hasher", AUDIT)
    from pathlib import Path

    path = Path(hasher["file_path"])
    assert path.is_file(), "the evidence bundle must exist before it is hashed"
    assert path.read_text(encoding="utf-8").startswith("{")
    verifier = audit._block_input("evidence_verifier", AUDIT)["input"]
    assert verifier["digest"] == audit._evidence_digest(AUDIT)
    assert verifier["control_id"] == "PCI-DSS-3.2"


@pytest.mark.pilot
def test_handlers_persist_one_record_each():
    from app import store
    from app.actions import inventory_management as inv

    env = pytest.importorskip("os")
    before = len(store.list_all(inv.ENTITY))
    inv.handle(dict(STOCK))
    rows = store.list_all(inv.ENTITY)
    assert len(rows) > before
    assert any(row.get("sku") == "SKU-1" for row in rows)
