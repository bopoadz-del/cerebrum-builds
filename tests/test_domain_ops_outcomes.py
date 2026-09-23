"""The ten business outcomes are performed, not asserted."""

from __future__ import annotations

import asyncio

import pytest

from app.domain_ops import OUTCOMES, execute_action, perform_all, spec_for
from app.domain_ops import authorized_context, unauthorized_context


def test_the_ten_outcomes_are_the_contract():
    assert len(OUTCOMES) == 10
    assert "create_persists" in OUTCOMES
    assert "queue_item_processed" in OUTCOMES
    assert "refused_action_errors" in OUTCOMES


def test_a_write_without_permission_is_permission_denied():
    result = execute_action(
        spec_for("create", "notification"),
        unauthorized_context("psi"),
        {"capability_id": "notification", "reference": "r", "status": "open", "trigger_event": "lead_qualified"},
    )
    assert result["status"] == "permission_denied"
    assert result["ok"] is False


def test_a_missing_required_field_is_invalid_input():
    result = execute_action(
        spec_for("create", "notification"),
        authorized_context("psi"),
        {"capability_id": "notification", "reference": "r", "status": "open"},
    )
    assert result["status"] == "validation_error"
    assert result["error_code"] == "invalid_input"
    assert "trigger_event" in str(result["error_message"])


def test_an_unknown_capability_is_named():
    result = execute_action(
        spec_for("create", "notification"), authorized_context("psi"), {"capability_id": "nope"}
    )
    assert result["error_code"] == "unknown_capability"


@pytest.mark.pilot
def test_all_ten_outcomes_are_performed_for_every_capability():
    from app.models import CAPABILITY_IDS

    failures = {}
    for capability in CAPABILITY_IDS:
        report = asyncio.run(perform_all(capability, tenant_id="psi"))
        if not report["ok"]:
            failures[capability] = report["failed"]
    assert failures == {}
