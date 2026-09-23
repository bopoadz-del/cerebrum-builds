"""Money refuses by name, and every answer says which layer it came from."""

from __future__ import annotations

import pytest

from app import config, formulas
from app.authority import Claim, envelope, precedence_document, resolve
from app.config import SettingMissing
# The factory TESTER role owns tests/conftest.py and may rewrite it, so a 
# fixture the console tests need is imported from the product's own helper 
# rather than declared in conftest (a missing 'client' fixture is an ERROR, 
# not a failure, and it took the whole file down with it).
from tests.callops_helpers import AUTH, client  # noqa: F401 - pytest fixture


def test_the_briefs_money_is_never_invented(monkeypatch):
    # config reads these from the environment on every call: no default exists
    # to be invented, so unsetting them is what "not configured" means.
    for name in ("CURRENCY", "VAT_RATE", "BROKER_COMMISSION_RATE"):
        monkeypatch.delenv(name, raising=False)
    assert config.env("CURRENCY") is None
    with pytest.raises(SettingMissing) as excinfo:
        formulas.price_with_tax(100)
    assert "CURRENCY" in str(excinfo.value)
    with pytest.raises(SettingMissing) as excinfo:
        formulas.broker_commission(1_000_000)
    assert "CURRENCY" in str(excinfo.value)


def test_the_formula_route_refuses_a_missing_setting_with_a_4xx(client, monkeypatch):
    monkeypatch.delenv("CURRENCY", raising=False)
    response = client.post("/v1/formulas/price_with_tax", json={"amount": 100}, headers=AUTH)
    assert 400 <= response.status_code < 500
    assert "CURRENCY" in response.json()["detail"]


def test_the_operator_owns_the_rate_and_the_currency(monkeypatch):
    monkeypatch.setenv("CURRENCY", "AED")
    monkeypatch.setenv("VAT_RATE", "5%")
    monkeypatch.setenv("BROKER_COMMISSION_RATE", "0.02")
    priced = formulas.price_with_tax(1_250_000)
    assert priced["currency"] == "AED"
    assert priced["result"] == 1_312_500.0
    assert priced["authority"]["layer"] == "formulas"
    commission = formulas.broker_commission(1_250_000)
    assert commission["result"] == 25_000.0


def test_precedence_ranks_certified_above_documents_above_formulas_above_procedures():
    document = precedence_document()
    assert document["id"] == "precedence.v1"
    assert [layer["layer"] for layer in document["layers"]] == [
        "certified",
        "documents",
        "formulas",
        "procedures",
    ]
    winner = resolve(
        [
            Claim(name="price", value="1,250,000", layer="procedures", source="script"),
            Claim(name="price", value="1,890,000", layer="documents", source="sheet#chunk-2"),
            Claim(name="price", value="1,250,000", layer="certified", source="signed-sheet"),
        ]
    )
    assert winner["layer"] == "certified"
    assert winner["label"].startswith("certified:")
    assert len(winner["claim_labels"]) == 3
    assert winner["divergence"], "two layers disagreed and both are recorded"


def test_an_answer_with_no_supporting_layer_is_withheld():
    empty = envelope([], withheld_claim="handover_date")
    assert empty["withheld"] is True
    assert empty["label"] == "withheld:handover_date"


def test_the_console_is_told_which_layer_answered(client):
    authority = client.get("/v1/authority", headers=AUTH).json()
    assert authority["precedence"]["id"] == "precedence.v1"
    dashboard = client.get("/v1/dashboard", headers=AUTH).json()
    assert dashboard["authority"]["layer"] == "formulas"
