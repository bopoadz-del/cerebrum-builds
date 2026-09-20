"""Domain-behaviour suite: the decisions the platform actually makes.

Written by the factory WRITER role (codewhale exec)

A handler that stores a row where the customer asked for a routing, a
service target or a permission check is not finished work. These tests
assert the decision, not the row.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

TOKEN = os.environ.setdefault("PLATFORM_TOKEN", "dev-local-token")
AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as booted:
        yield booted


# -- the formula layer -----------------------------------------------------


def test_priority_sets_the_service_target_and_the_deadline():
    from app import formulas

    critical = formulas.response_target_hours("critical")
    low = formulas.response_target_hours("low")
    assert critical < low
    due = formulas.sla_due_at("2026-09-03T08:00:00", critical)
    assert due.startswith("2026-09-03T12:00:00")
    assert formulas.sla_breach(
        due_at=due, closed_at="2026-09-03T13:00:00"
    ) is True
    assert formulas.sla_breach(
        due_at=due, closed_at="2026-09-03T09:00:00"
    ) is False


def test_service_target_is_an_operator_setting_not_a_constant(monkeypatch):
    from app import formulas

    monkeypatch.setenv("SLA_CRITICAL_HOURS", "1.5")
    assert formulas.response_target_hours("critical") == 1.5


def test_match_score_prefers_the_right_trade_over_a_free_technician():
    from app import formulas

    right_trade = formulas.match_score(
        trade_match=True, skill_match=True, same_school=True,
        workload=10, priority="high",
    )
    wrong_trade = formulas.match_score(
        trade_match=False, skill_match=False, same_school=False,
        workload=90, priority="high",
    )
    assert right_trade > wrong_trade
    assert 0.0 <= wrong_trade <= 100.0


def test_formulas_refuse_rather_than_invent():
    from app import formulas

    with pytest.raises(formulas.FormulaError):
        formulas.utilisation_pct(open_jobs=4, headcount=0)
    with pytest.raises(formulas.FormulaError):
        formulas.sla_compliance_pct(within_target=5, total=0)
    with pytest.raises(formulas.FormulaError):
        formulas.match_score(workload=150)


def test_portfolio_total_names_the_records_it_cannot_sum():
    from app import formulas

    with pytest.raises(formulas.FormulaError) as caught:
        formulas.portfolio_total(
            [{"complaints_open": 2}, {"complaints_open": "many"}],
            key="complaints_open",
        )
    assert "record 1" in str(caught.value)


# -- the decisions ---------------------------------------------------------


def test_complaint_is_triaged_with_a_target_and_an_escalation(client):
    from app.models import MODELS

    body = {
        "reference": "CMP-TRIAGE-1",
        "status": "open",
        "school": "deira-primary",
        "category": "hvac",
        "priority": "critical",
        "description": "AC failure in the Year 4 block",
        "raised_by": "year4.parent@example.com",
        "raised_by_role": "parent",
    }
    assert set(MODELS["complaints_management"].FIELDS) >= set(body)
    answer = client.post(
        "/v1/complaints_management", json=body, headers=AUTH
    ).json()
    assert answer.get("ok") is True, answer
    triage = answer["result"]["output"]["platform"]["triage"]
    assert triage["required_trade"] == "hvac"
    assert triage["sla_hours"] == 4
    assert triage["escalate"] is True
    assert triage["due_at"].startswith("20")


def test_cleaning_and_grounds_go_to_cleaners_and_trades_to_technicians(client):
    from app.models import MODELS

    def route(category):
        body = {
            "reference": "ASG-" + category,
            "status": "open",
            "complaint_reference": "CMP-1",
            "school": "mirdif-primary",
            "category": category,
            "priority": "medium",
            "required_trade": category,
            "required_skill": "",
            "assigned_to": "field-1",
            "assignment_mode": "auto",
        }
        assert set(MODELS["auto_assignment"].FIELDS) >= set(body)
        return client.post("/v1/auto_assignment", json=body, headers=AUTH).json()["result"]["output"]

    assert route("cleaning")["platform"]["routing"]["assigned_role"] == "cleaner"
    assert route("electrical")["platform"]["routing"]["assigned_role"] == "technician"


def test_a_manual_override_must_carry_its_reason(client):
    from app.models import MODELS

    body = {
        "reference": "ASG-OVERRIDE-1",
        "status": "open",
        "complaint_reference": "CMP-2",
        "school": "karama-secondary",
        "category": "plumbing",
        "priority": "high",
        "required_trade": "plumbing",
        "assignment_mode": "manual",
    }
    assert set(MODELS["auto_assignment"].FIELDS) >= set(body)
    answer = client.post("/v1/auto_assignment", json=body, headers=AUTH).json()
    assert answer["result"]["output"]["platform"]["routing"]["override_reason_required"] is True


def test_team_load_is_computed_against_the_platform_cap(client):
    from app.models import MODELS

    body = {
        "reference": "TEAM-1",
        "status": "open",
        "school": "jumeirah-primary",
        "team_name": "jumeirah-technicians",
        "team_type": "technician",
        "shift": "morning",
        "headcount": 2,
        "open_jobs": 20,
    }
    assert set(MODELS["workforce_management"].FIELDS) >= set(body)
    answer = client.post(
        "/v1/workforce_management", json=body, headers=AUTH
    ).json()
    state = answer["result"]["output"]["platform"]["team_state"]
    assert state["capacity"] == 10.0
    assert state["spare_capacity"] == 0.0
    assert state["under_staffed"] is True


def test_a_role_may_not_widen_its_own_scope(client):
    from app.models import MODELS

    body = {
        "reference": "RBA-1",
        "status": "open",
        "principal": "cleaner-7",
        "role": "cleaner",
        "school": "warqa-secondary",
        "access_scope": "portfolio",
    }
    assert set(MODELS["role_based_access"].FIELDS) >= set(body)
    answer = client.post("/v1/role_based_access", json=body, headers=AUTH).json()
    grant = answer["result"]["output"]["platform"]["grant"]
    assert grant["access_scope"] == "assigned_jobs"
    assert "scope_refused" in grant
    assert "access:grant" not in grant["permissions"]


def test_a_portfolio_report_is_rated_per_school(client):
    from app.models import MODELS

    body = {
        "reference": "RPT-1",
        "status": "open",
        "report_type": "monthly",
        "scope": "portfolio",
        "school": "estate",
        "period_start": "2026-09-01",
        "period_end": "2026-09-30",
        "complaints_total": 250,
        "closed_total": 200,
    }
    assert set(MODELS["reporting"].FIELDS) >= set(body)
    answer = client.post("/v1/reporting", json=body, headers=AUTH).json()
    report = answer["result"]["output"]["platform"]["report"]
    assert report["open_total"] == 50.0
    assert report["complaints_per_school"] == 25.0


def test_the_console_drives_more_than_one_capability_and_shows_authority(client):
    page = client.get("/")
    assert page.status_code == 200
    html = page.text
    assert "/v1/capabilities" in html
    authority = client.get("/v1/authority", headers=AUTH).json()
    assert authority["version"] == "precedence.v1"
    assert any(layer["layer"] == "formulas" for layer in authority["layers"])
    assert authority["label"]["authority"]
