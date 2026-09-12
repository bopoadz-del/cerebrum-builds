"""HotelOps A: non-trivial inventory, pipeline, quote, service, CRM, pack logic."""

from __future__ import annotations

import pytest

from app.actions.car_dealership_core import (
    _amortized_monthly,
    _finance_quote,
    _lease_monthly,
    handle,
    vin_check_digit_ok,
)

pytestmark = pytest.mark.not_pilot

SCHEMA_SAMPLE = {
    "reference": "sample",
    "status": "open",
    "vin": "sample",
    "customer_name": "sample",
    "deal_type": "retail",
}


def test_schema_sample_quote_is_not_zero(isolated_storage) -> None:
    result = handle(SCHEMA_SAMPLE)
    assert result["ok"] is True
    quote = result["record"]["finance_quote"]
    assert quote["monthly"] > 0
    assert quote["amount_financed"] > 0
    assert quote["term_months"] == 60
    assert quote["apr_bps"] > 0
    assert quote["quote_basis"] == "retail_cash_plus_conventional"


def test_lease_and_finance_quotes_differ(isolated_storage) -> None:
    finance = _finance_quote({**SCHEMA_SAMPLE, "deal_type": "finance"})
    lease = _finance_quote({**SCHEMA_SAMPLE, "deal_type": "lease"})
    assert finance["monthly"] > 0
    assert lease["monthly"] > 0
    assert finance["term_months"] == 60
    assert lease["term_months"] == 36
    assert lease["residual"] > 0
    assert lease["quote_basis"] == "lease_money_factor"
    assert finance["monthly"] != lease["monthly"]


def test_amortized_payment_matches_known_value() -> None:
    # $10,000 at 6% for 36 months ≈ $304.22
    assert _amortized_monthly(10000.0, 6.0, 36) == 304.22


def test_lease_payment_uses_money_factor() -> None:
    monthly = _lease_monthly(30000.0, 16500.0, 0.00249, 36)
    depreciation = (30000.0 - 16500.0) / 36
    rent = (30000.0 + 16500.0) * 0.00249
    assert monthly == round(depreciation + rent, 2)
    assert monthly > 0


def test_pipeline_and_pack_transition_with_status(isolated_storage) -> None:
    opened = handle({**SCHEMA_SAMPLE, "status": "open"})["record"]
    live = handle({**SCHEMA_SAMPLE, "status": "in_progress", "reference": "desk-1"})["record"]
    closed = handle({**SCHEMA_SAMPLE, "status": "closed", "reference": "sold-1"})["record"]

    assert opened["sales_pipeline"]["stage"] == "lead"
    assert opened["sales_pipeline"]["allowed_next_status"] == ["in_progress"]
    assert live["sales_pipeline"]["stage"] == "f_and_i"
    assert live["sales_pipeline"]["can_close"] is True
    assert closed["sales_pipeline"]["stage"] == "delivered"
    assert closed["sales_pipeline"]["is_terminal"] is True

    assert opened["vehicle_inventory"][0]["availability"] == "available"
    assert live["vehicle_inventory"][0]["availability"] == "reserved"
    assert closed["vehicle_inventory"][0]["availability"] == "sold"

    assert opened["service_appointment"]["slot"] == "unscheduled"
    assert live["service_appointment"]["slot"] == "checked_in"
    assert closed["service_appointment"]["slot"] == "closed_ro"

    open_docs = {row["doc"]: row["status"] for row in opened["deal_document_pack"]}
    live_docs = {row["doc"]: row["status"] for row in live["deal_document_pack"]}
    closed_docs = {row["doc"]: row["status"] for row in closed["deal_document_pack"]}
    assert open_docs["buyers_order"] == "open"
    assert live_docs["buyers_order"] == "in_progress"
    assert live_docs["finance_or_lease_contract"] == "open"
    assert all(status == "closed" for status in closed_docs.values())
    assert all(row["signed_at"] for row in closed["deal_document_pack"])


def test_crm_and_inventory_fields(isolated_storage) -> None:
    record = handle({**SCHEMA_SAMPLE, "customer_name": "Ada Cole", "vin": "1HGCM82633A004352"})[
        "record"
    ]
    assert record["customer_crm"]["source"] == "showroom"
    assert record["customer_crm"]["last_touch"] == "lead_capture"
    assert record["vehicle_inventory"][0]["asking_price"] > 0
    assert record["vehicle_inventory"][0]["stock_number"] == "sample"


def test_vin_check_digit() -> None:
    assert vin_check_digit_ok("sample") is False
    assert vin_check_digit_ok("1HGCM82633A004352") is True
    assert vin_check_digit_ok("1HGCM82633A004353") is False
