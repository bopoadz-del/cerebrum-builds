"""The versioned formula registry (precedence layer 3).

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

import pytest

from app import formulas


def test_registry_is_versioned_data():
    catalogue = formulas.registry()
    assert catalogue
    for entry in catalogue:
        assert entry["id"] and entry["version"] and entry["unit"]
        assert entry["params"] and entry["expression"]


def test_compute_returns_the_documented_unit():
    out = formulas.compute(
        "stay_charge_projection",
        {"nightly_rate": 125.0, "nights": 3},
    )
    assert out["result"] == pytest.approx(375.0)
    assert out["unit"] == "currency"
    assert out["version"] == "1.0.0"


def test_missing_parameters_are_refused_not_guessed():
    with pytest.raises(formulas.FormulaError):
        formulas.compute("stay_charge_projection", {"nightly_rate": 100.0})


def test_unknown_formula_is_refused():
    with pytest.raises(formulas.FormulaError):
        formulas.lookup("does_not_exist")


def test_expression_cannot_reach_outside_the_whitelist():
    with pytest.raises(formulas.FormulaError):
        formulas._safe_eval("__import__('os').system('true')", {})
