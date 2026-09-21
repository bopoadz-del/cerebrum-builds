"""The domain decisions CallOps was asked to make, end to end."""

from __future__ import annotations

from app import domain, formulas
from tests.callops_helpers import (  # noqa: F401 - client is a fixture
    AUTH, client, payload_for,
)


def test_a_lead_file_becomes_a_paced_dial_list(client):
    csv_text = (
        "name,phone,language,project\n"
        "Fatima Al Ali,+971501234567,ar,az-zahra\n"
        "Omar Haddad,00971509876543,en,az-zahra\n"
        "No Phone,,en,az-zahra\n"
    )
    response = client.post(
        "/v1/leads/import",
        json={"text": csv_text, "campaign": "psi-q3", "file_name": "leads.csv"},
        headers=AUTH,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["accepted"] == 2
    assert any("name or phone missing" in str(row.get("reason")) for row in body["refused"])
    queued = [row for row in body["queued"] if row["dialable"]]
    assert queued, "a normalisable number must enter the dial list"
    assert all(row["queue_state"] in ("queued", "held") for row in body["queued"])

    listing = client.get("/v1/dial-queue?campaign=psi-q3", headers=AUTH)
    assert listing.status_code == 200
    queue = listing.json()
    assert queue["cap"]["formula"] == "calls_remaining"
    assert queue["pacing"]["result"] >= 0
    assert queue["authority"]["layer"] == "formulas"


def test_a_number_without_a_country_code_is_held_not_guessed(client):
    response = client.post(
        "/v1/leads/import",
        json={"text": "name,phone\nYousef,0501234567\n", "campaign": "psi-q3", "project_tag": "az-zahra"},
        headers=AUTH,
    )
    assert response.status_code == 200
    row = response.json()["queued"][0]
    assert row["dialable"] is False
    assert row["queue_state"] == "held"
    assert "country code" in row["reason"]


def test_the_state_machine_walks_a_call_and_ledgers_every_step(client):
    call_sid = "CAflow0000000000000000000000001"
    steps = [
        ("dial", "queued", "dialing"),
        ("answer", "dialing", "answered"),
        ("pitch", "answered", "pitched"),
        ("qualify", "pitched", "qualified"),
        ("transfer", "qualified", "transferred"),
        ("close", "transferred", "closed"),
    ]
    transitions = 0
    for event, previous, expected in steps:
        body = payload_for(
            "call_state_machine", call_sid=call_sid, event=event, previous_state=previous
        )
        response = client.post("/v1/call_state_machine", json=body, headers=AUTH)
        assert response.status_code == 200, response.text
        result = response.json()["result"]
        transitions += 1
        # Every transition leaves a call event behind: the prepared event_bus
        # child is published before the decision is answered, and a publish
        # that fails is reported as this capability failing.
        assert result["event"]["published"] is True
        assert result["event"]["channel"] == "mcp"
        if event == "dial":
            # The dial is guarded by the call window, so this either opens the
            # call or refuses it with the window named — never a silent skip.
            assert result["transition_allowed"] in (True, False)
            if not result["transition_allowed"]:
                assert "window" in result["refusal_reason"]
                continue
        assert result["transition_allowed"] is True, result["refusal_reason"]
        assert response.json()["stored"]["current_state"] == expected

    # The transitions are already on the chain, so the explicit ledger events
    # continue it rather than restarting at sequence 1.
    sequences = []
    for event in [
        "attempted", "initiated", "answered", "pitched", "qualified",
        "transfer_started", "transfer_completed", "call_ended",
    ]:
        body = payload_for(
            "outcome_capture_and_ledger", call_sid=call_sid, event_type=event, outcome="project_interested"
        )
        response = client.post("/v1/outcome_capture_and_ledger", json=body, headers=AUTH)
        assert response.status_code == 200
        stored = response.json()["stored"]
        sequences.append(stored["sequence"])
        assert response.json()["result"]["chain_intact"] is True
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)

    history = client.get(f"/v1/calls/{call_sid}", headers=AUTH)
    assert history.status_code == 200
    body = history.json()
    assert body["history"]["events"] == transitions + 8
    assert body["history"]["chain"]["intact"] is True


def test_a_tampered_ledger_entry_is_detected(client):
    call_sid = "CAflow0000000000000000000000002"
    for event in ("attempted", "answered", "call_ended"):
        client.post(
            "/v1/outcome_capture_and_ledger",
            json=payload_for("outcome_capture_and_ledger", call_sid=call_sid, event_type=event),
            headers=AUTH,
        )
    from app import store
    from tests.callops_helpers import TENANT

    rows = [
        row
        for row in store.list_all("outcome_capture_and_ledger", TENANT)
        if row["call_sid"] == call_sid
    ]
    rows[1]["payload_digest"] = "0" * 64
    report = domain.verify_chain(rows)
    assert report["intact"] is False
    assert report["violations"]


def test_qualification_is_a_schema_and_the_summary_comes_from_it(client):
    response = client.post(
        "/v1/qualification_and_broker_summary",
        json=payload_for(
            "qualification_and_broker_summary",
            call_sid="CAflow0000000000000000000000003",
            outcome="project_interested",
            transcript="I want a two bedroom apartment, budget around 2 million, handover in six months",
        ),
        headers=AUTH,
    )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["outcome"] == "project_interested"
    assert result["summary"]["collected"]["property_type"] == "apartment"
    assert result["summary"]["collected"]["budget"] == 2000000.0
    assert result["summary"]["collected"]["timeline"] == "six_months"
    assert result["next_action"] == "transfer_to_broker"
    stored = response.json()["stored"]
    assert stored["qualified"]
    assert stored["authority_label"]


def test_a_not_interested_lead_is_never_transferred(client):
    response = client.post(
        "/v1/qualification_and_broker_summary",
        json=payload_for(
            "qualification_and_broker_summary",
            call_sid="CAflow0000000000000000000000004",
            outcome="not_interested",
        ),
        headers=AUTH,
    )
    body = response.json()
    assert body["result"]["transfer_required"] is False
    assert body["stored"]["next_action"] == "close_lead"
    transfer = client.post(
        "/v1/warm_transfer",
        json=payload_for(
            "warm_transfer",
            call_sid="CAflow0000000000000000000000004",
            outcome="transferred",
            qualified_outcome="not_interested",
        ),
        headers=AUTH,
    )
    assert transfer.json()["result"]["decision"] == "no_qualification"


def test_campaign_metrics_split_interest_three_ways(client):
    for index, outcome in enumerate(
        ["project_interested", "other_re_interested", "not_interested"], start=1
    ):
        call_sid = f"CAmetrics00000000000000000000000{index}"
        client.post(
            "/v1/call_state_machine",
            json=payload_for("call_state_machine", call_sid=call_sid, event="dial", previous_state="queued", current_state="answered", campaign="psi-q3"),
            headers=AUTH,
        )
        client.post(
            "/v1/qualification_and_broker_summary",
            json=payload_for("qualification_and_broker_summary", call_sid=call_sid, outcome=outcome, campaign="psi-q3"),
            headers=AUTH,
        )
    dashboard = client.get("/v1/dashboard?campaign=psi-q3", headers=AUTH)
    assert dashboard.status_code == 200
    metrics = dashboard.json()["metrics"]
    assert set(metrics["interest"]) == {"project_interested", "other_re_interested", "not_interested"}
    assert metrics["qualified"] >= 3
    assert dashboard.json()["authority"]["layer"] == "formulas"
    assert "<svg" in (dashboard.json()["chart"] or "")


def test_the_queue_processor_claims_and_processes_an_item(client):
    client.post(
        "/v1/leads/import",
        json={"text": "name,phone,language,project\nDiala,+971502223344,en,az-zahra\n", "campaign": "psi-q3"},
        headers=AUTH,
    )
    depth = client.get("/v1/dial-queue?campaign=psi-q3", headers=AUTH).json()["depth"]
    assert depth["pending"] >= 1
    from app import work_queue
    from tests.callops_helpers import TENANT

    pending = [item for item in work_queue.list_all(tenant_id=TENANT) if item["status"] == work_queue.PENDING]
    item_id = pending[-1]["id"]
    claimed = client.post(f"/v1/dial-queue/{item_id}/claim", headers=AUTH)
    assert claimed.status_code == 200
    assert claimed.json()["item"]["status"] == work_queue.PROCESSING
    again = client.post(f"/v1/dial-queue/{item_id}/claim", headers=AUTH)
    assert again.status_code == 404, "a claimed item is not claimable twice"
    processed = client.post(f"/v1/dial-queue/{item_id}/process", headers=AUTH)
    assert processed.status_code in (200, 409)
    if processed.status_code == 200:
        assert processed.json()["item"]["status"] == work_queue.PROCESSED
        assert processed.json()["result"]["ok"] is True


def test_formulas_stay_the_operators_to_change(monkeypatch):
    capped = formulas.calls_remaining(daily_cap=10, attempted_today=4)
    assert capped["result"] == 6
    assert capped["cap_reached"] is False
    assert formulas.calls_remaining(daily_cap=10, attempted_today=10)["cap_reached"] is True
    first = formulas.retry_backoff(attempt=1)
    second = formulas.retry_backoff(attempt=2)
    third = formulas.retry_backoff(attempt=3)
    assert first["result"] < second["result"]
    assert third["exhausted"] is True and third["next_attempt"] is None
    window = formulas.best_call_window(language="ar", windows="22:00-23:00")
    assert window["inside_window"] is False
    assert window["authority"]["layer"] == "formulas"
