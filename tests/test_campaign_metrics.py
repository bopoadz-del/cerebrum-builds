"""Campaign outcome metrics (Layer 4): the numbers, and the refusals.

Written by the factory WRITER role (codewhale exec)

Counter-cases here are named from this brief, not from a shape carried over
from another product:

* the metric vocabulary is the brief's -- attempted, answered, the three
  outcome split, transfers, conversion -- and the outcome enum in
  app/analytics_metrics.py is asserted equal to the enum the schema declares
  (app/models.py), so the two cannot drift;
* a campaign name that appears on no row answers zeros, and never a
  campaign the platform invented;
* a row carrying an outcome outside the three-outcome vocabulary is reported
  as unmapped, never counted as interest;
* the boundary is exercised exactly on the line: one transfer out of two
  attempts is 50.0% conversion, and one transfer out of one attempt is
  100.0% -- not either side of it;
* a zero base is 0.0% (nothing attempted), not a division error;
* a malformed row (not a dict, no call_sid, no campaign) does not vanish from
  the attempted count and does not crash the read model;
* a caller who presents a principal this deployment does not know sees an
  empty namespace, not the platform tenant's numbers (multi-tenant mode);
* an unknown query field is refused by name rather than ignored.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app import analytics_metrics, formulas
from app.main import app
from app.models import MODELS

client = TestClient(app)
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}

LEDGER = "outcome_capture_and_ledger"
CAMPAIGN = "psi-marina-q3"
CAMPAIGN_B = "psi-hills-q4"


def _row(sid, event, campaign=CAMPAIGN, outcome=None, reference=None):
    row = {
        "reference": reference or ("ledger-" + str(sid) + "-" + event),
        "status": "open",
        "call_sid": sid,
        "campaign": campaign,
        "event_type": event,
    }
    if outcome is not None:
        row["outcome"] = outcome
    return row


def _post(row):
    resp = client.post("/v1/" + LEDGER, json=row, headers=AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("ok") is True, body
    return body


# --- the metric vocabulary is the schema's, not prose ---------------------


def test_outcome_enum_is_the_schema_enum():
    declared = MODELS["qualification_and_broker_summary"].CONSTRAINTS["outcome"]["allowed_values"]
    assert list(analytics_metrics.OUTCOMES) == list(declared)


def test_metric_list_is_the_briefs():
    assert analytics_metrics.metric_names() == [
        "attempted",
        "answered",
        "answered_rate",
        "interest",
        "transfers",
        "conversion",
    ]


# --- the arithmetic, exactly on the line ----------------------------------


def test_conversion_boundary_exactly_on_the_line():
    assert formulas.conversion_rate(2, 1) == 50.0
    assert formulas.conversion_rate(1, 1) == 100.0
    assert formulas.conversion_rate(3, 1) == 33.33
    assert formulas.percent_of(1, 3) == 33.33


def test_zero_base_is_zero_not_an_error():
    assert formulas.conversion_rate(0, 0) == 0.0
    assert formulas.percent_of(5, 0) == 0.0


# --- aggregation over real ledger rows ------------------------------------


def test_campaign_metrics_counts_from_the_ledger():
    _post(_row("CA-M1", "attempt"))
    _post(_row("CA-M1", "answer"))
    _post(_row("CA-M1", "outcome", outcome="project_interested"))
    _post(_row("CA-M1", "transfer"))
    _post(_row("CA-M2", "attempt"))
    _post(_row("CA-M2", "answer"))
    _post(_row("CA-M2", "outcome", outcome="not_interested"))
    resp = client.get("/v1/analytics/campaign_metrics?campaign=" + CAMPAIGN, headers=AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["campaign_filter"] == CAMPAIGN
    assert body["campaigns"], body
    metrics = [item for item in body["campaigns"] if item["campaign"] == CAMPAIGN][0]
    assert metrics["attempted"] == 2
    assert metrics["answered"] == 2
    assert metrics["transfers"] == 1
    assert metrics["answered_rate"] == 100.0
    assert metrics["transfer_rate"] == 50.0
    assert metrics["conversion"] == 50.0
    assert metrics["interest"]["project_interested"] == 1
    assert metrics["interest"]["not_interested"] == 1
    assert metrics["interest"]["other_re_interested"] == 0
    # a computed metric is layer 3 and says so
    assert body["authority"] == "formulas"
    assert body["precedence"] == "precedence.v1"
    assert body["rank"] == 3


def test_campaign_with_no_rows_answers_zeros_not_an_invented_name():
    resp = client.get("/v1/analytics/campaign_metrics?campaign=no-such-campaign", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert len(body["campaigns"]) == 1
    only = body["campaigns"][0]
    assert only["campaign"] == "no-such-campaign"
    assert only["attempted"] == 0
    assert only["answered"] == 0
    assert only["transfers"] == 0
    assert only["conversion"] == 0.0
    assert only["ledger_events"] == 0


def test_unknown_query_field_is_refused_by_name():
    resp = client.get("/v1/analytics/campaign_metrics?sql=select%201", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "sql" in body["error"]


# --- counter-cases: the refusals ------------------------------------------


def test_outcome_outside_the_enum_is_refused_at_the_edge():
    bad = _row("CA-M3", "outcome", outcome="warm_lead")
    resp = client.post("/v1/" + LEDGER, json=bad, headers=AUTH)
    assert resp.status_code == 422, resp.text
    assert "outcome" in str(resp.json().get("detail"))


def test_row_with_unknown_outcome_is_reported_not_counted_as_interest():
    rows = [
        {"call_sid": "CA-M4", "campaign": CAMPAIGN, "event_type": "outcome", "outcome": "maybe"},
    ]
    body = analytics_metrics.campaign_metrics(rows, campaign=CAMPAIGN)
    metrics = body["campaigns"][0]
    assert metrics["interest"] == {
        "project_interested": 0,
        "other_re_interested": 0,
        "not_interested": 0,
    }
    assert metrics["unmapped_outcomes"] == {"maybe": 1}


def test_malformed_rows_do_not_crash_and_do_not_vanish():
    rows = [
        "not-a-dict",
        {"event_type": "attempt"},  # no call_sid, no campaign
        {"call_sid": "CA-M5", "campaign": CAMPAIGN, "event_type": "attempt"},
    ]
    body = analytics_metrics.campaign_metrics(rows)
    campaigns = {item["campaign"]: item for item in body["campaigns"]}
    assert campaigns[analytics_metrics.UNATTRIBUTED]["attempted"] == 1
    assert campaigns[CAMPAIGN]["attempted"] == 1
    assert body["totals"]["attempted"] == 2


def test_unknown_principal_sees_an_empty_namespace(monkeypatch):
    """The numbers are the tenant's own -- a principal this deployment does not
    know is not folded into the platform tenant."""
    _post(_row("CA-M6", "attempt"))
    ok = client.get("/v1/analytics/campaign_metrics", headers=AUTH)
    assert ok.status_code == 200
    assert ok.json()["totals"]["attempted"] >= 1
    monkeypatch.setenv("TENANT_TOKENS", "token-a:tenant-a,token-b:tenant-b")
    other = client.get(
        "/v1/analytics/campaign_metrics", headers={"Authorization": "Bearer token-b"}
    )
    assert other.status_code == 200
    body = other.json()
    assert body["totals"]["attempted"] == 0
    assert all(item["attempted"] == 0 for item in body["campaigns"])


def test_unknown_token_reads_its_own_empty_namespace(monkeypatch):
    """Read doctrine: a principal this deployment does not know is never
    folded into the operator's tenant -- it reads its own, empty namespace."""
    _post(_row("CA-M7", "attempt"))
    monkeypatch.setenv("TENANT_TOKENS", "token-a:tenant-a")
    resp = client.get(
        "/v1/analytics/campaign_metrics", headers={"Authorization": "Bearer nope"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["totals"]["attempted"] == 0
    assert body["campaigns"] == []


def test_write_route_without_a_token_is_401():
    """The floor: every write refuses an unauthenticated request by name."""
    resp = client.post("/v1/" + LEDGER, json=_row("CA-M8", "attempt"), headers={})
    assert resp.status_code == 401, resp.text
    assert resp.json()["detail"] == "authentication_required"


def test_console_drives_the_metrics_route():
    """The served console is wired to this route, not a list of paths."""
    page = client.get("/")
    assert page.status_code == 200
    assert "text/html" in page.headers.get("content-type", "")
    assert "/v1/analytics/campaign_metrics" in page.text
    assert "loadCampaignMetrics" in page.text
