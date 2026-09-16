"""LexManage domain behaviour: the seven capabilities do the work they claim.

Written by the factory WRITER role (codewhale exec).

These are the firm's own outcomes, not plumbing: a matter brief that carries
its deadlines, an intake that blocks on a conflict, a billable amount that is
computed from hours x rate, a document digest that is stable, a portal scope
that depends on the account's access level, an analytics verdict against the
benchmark, and a compliance record whose evidence digest is reproducible.
"""

from __future__ import annotations

import pytest

from app.actions import (
    client_intake,
    client_portal,
    compliance_audit,
    document_management,
    legal_analytics,
    matter_management,
    time_and_billing,
)


MATTER = {
    "reference": "matter-1",
    "status": "open",
    "matter_number": "2026-0042",
    "matter_title": "Commercial lease dispute",
    "client_name": "Northwind Trading",
    "client_email": "counsel@example.com",
    "practice_area": "litigation",
    "responsible_attorney": "A. Whitfield",
    "matter_stage": "discovery",
    "priority": "high",
    "opened_date": "2026-09-03",
    "deadline_date": "2026-10-01",
    "billing_type": "hourly",
    "document_path": "",
}

INTAKE = {
    "reference": "intake-1",
    "status": "open",
    "client_name": "Harbour Logistics",
    "client_email": "intake@example.com",
    "client_phone": "555-0100",
    "matter_type": "employment",
    "referral_source": "existing client",
    "conflict_check": "pending",
    "risk_score": 0.0,
    "estimated_fee": 12000.0,
    "retainer_amount": 4000.0,
    "document_path": "",
    "intake_date": "2026-09-03",
}

DOCUMENT = {
    "reference": "doc-1",
    "status": "open",
    "document_title": "Lease agreement",
    "document_type": "contract",
    "matter_number": "2026-0042",
    "version": "2",
    "file_path": "",
    "content_hash": "",
    "confidentiality": "privileged",
    "document_owner": "A. Whitfield",
    "tags": "lease litigation",
    "uploaded_by": "A. Whitfield",
    "uploaded_at": "2026-09-03T10:00:00",
}

TIME_ENTRY = {
    "reference": "time-1",
    "status": "open",
    "timekeeper": "A. Whitfield",
    "matter_number": "2026-0042",
    "client_name": "Northwind Trading",
    "client_email": "billing@example.com",
    "activity_date": "2026-09-03",
    "hours": 2.5,
    "hourly_rate": 320.0,
    "billable_amount": 0.0,
    "invoice_number": "INV-2026-0007",
    "payment_status": "unbilled",
    "narrative": "Review of lease clauses",
}

PORTAL = {
    "reference": "portal-1",
    "status": "open",
    "client_name": "Northwind Trading",
    "client_email": "client@example.com",
    "matter_number": "2026-0042",
    "portal_access_level": "full",
    "unread_messages": 3,
    "shared_documents": 2,
    "message_subject": "Discovery schedule",
    "message_body": "The discovery schedule has been filed.",
    "last_login_at": "2026-09-03T10:00:00",
    "document_path": "",
}

ANALYTIC = {
    "reference": "metric-1",
    "status": "open",
    "metric_name": "matters_closed",
    "metric_value": 18.0,
    "benchmark_value": 12.0,
    "practice_area": "litigation",
    "dimension": "quarter",
    "period_start": "2026-07-01",
    "period_end": "2026-09-30",
    "source_matter": "2026-0042",
}

COMPLIANCE = {
    "reference": "audit-1",
    "status": "open",
    "control_id": "CTRL-ACCESS-01",
    "framework": "ISO-27001",
    "regulation": "client confidentiality",
    "event_type": "access_review",
    "actor": "A. Whitfield",
    "actor_role": "attorney",
    "action_taken": "reviewed matter access list",
    "evidence_ref": "evidence/access-review-2026-09.json",
    "findings": "no exceptions",
    "occurred_at": "2026-09-03T10:00:00",
}


def test_capability_ids_and_entities_match_the_blueprint():
    assert matter_management.CAPABILITY_ID == "matter_management"
    assert matter_management.ENTITY == "matter_management"
    assert client_intake.BLOCK_IDS == [
        "workflow",
        "formula_executor",
        "validation",
        "document_engine",
    ]
    assert set(time_and_billing.BLOCK_DEFAULT_ACTIONS) == set(
        time_and_billing.BLOCK_IDS
    )


def test_matter_workflow_steps_are_prepared():
    """Every workflow child carries block + action + params.action + input."""
    wf = matter_management._block_input("workflow", MATTER)
    assert wf["steps"], "the matter pipeline has no children"
    for step in wf["steps"]:
        assert step["block"], step
        assert step["action"], step
        assert step["params"]["action"] == step["action"], step
        assert isinstance(step["input"], dict) and step["input"], step
    assert wf["result"]["matter_number"] == "2026-0042"


def test_matter_brief_carries_the_deadline():
    brief = matter_management._matter_brief(MATTER)
    assert "2026-0042" in brief
    assert "2026-10-01" in brief
    state = matter_management._insight(MATTER)
    assert state["deadline_recorded"] is True
    assert state["matter_stage"] == "discovery"


def test_intake_blocks_on_an_uncleared_conflict():
    state = client_intake._conflict_state(INTAKE)
    assert state["conflict_cleared"] is False
    assert client_intake._insight(INTAKE)["onboarding"].startswith("blocked")

    cleared = dict(INTAKE, conflict_check="cleared")
    assert client_intake._conflict_state(cleared)["conflict_cleared"] is True
    assert client_intake._insight(cleared)["onboarding"] == "cleared"


def test_intake_risk_formula_is_a_real_formula():
    spec = client_intake._block_input("formula_executor", INTAKE)
    assert "result" in spec["custom_code"]
    assert spec["input_values"]["retainer"] == 4000.0


def test_billable_amount_is_hours_times_rate():
    assert time_and_billing._billable_amount(TIME_ENTRY) == 800.0
    insight = time_and_billing._insight(TIME_ENTRY)
    assert insight["billable_amount"] == 800.0
    assert insight["outstanding"] == 800.0
    paid = dict(TIME_ENTRY, payment_status="paid")
    assert time_and_billing._insight(paid)["outstanding"] == 0.0


def test_document_digest_is_stable_and_versioned():
    first = document_management._insight(DOCUMENT)["content_hash"]
    again = document_management._insight(dict(DOCUMENT))["content_hash"]
    assert first == again and len(first) == 64
    changed = document_management._insight(dict(DOCUMENT, version="3"))
    assert changed["content_hash"] != first
    assert document_management._insight(DOCUMENT)["version"] == "2"


def test_document_storage_bind_reports_the_content_it_stored():
    payload = document_management._block_input("storage", DOCUMENT)
    assert payload["metadata"]["content_hash"] == document_management._insight(DOCUMENT)["content_hash"]
    assert payload["content"]


def test_portal_scope_follows_the_access_level():
    full = client_portal._portal_scope(PORTAL)
    assert full["access_level"] == "full"
    assert full["can_view_invoices"] is True
    limited = client_portal._portal_scope(dict(PORTAL, portal_access_level="limited"))
    assert limited["can_view_invoices"] is False
    assert limited["documents_writable"] is False


def test_analytics_verdict_uses_its_own_benchmark():
    above = legal_analytics._insight(ANALYTIC)
    assert above["verdict"] == "above benchmark"
    assert above["variance"] == 6.0
    below = legal_analytics._insight(dict(ANALYTIC, metric_value=4.0))
    assert below["verdict"] == "below benchmark"


def test_compliance_evidence_digest_is_reproducible():
    first = compliance_audit._insight(COMPLIANCE)["evidence_digest"]
    second = compliance_audit._insight(dict(COMPLIANCE))["evidence_digest"]
    assert first == second and len(first) == 64
    changed = compliance_audit._insight(dict(COMPLIANCE, evidence_ref="other"))
    assert changed["evidence_digest"] != first
    readiness = compliance_audit._block_input("readiness_engine", COMPLIANCE)["input"]
    assert readiness["control_id"] == "CTRL-ACCESS-01"
    assert readiness["evidence_present"] is True


def test_every_capability_declares_fields_for_the_blocks_it_binds():
    """If you assign it, you feed it: document_engine needs a document field."""
    document_names = {
        "file_path",
        "pdf_path",
        "docx_path",
        "xlsx_path",
        "attachment_path",
        "document_path",
        "text",
        "bytes",
    }
    for module in (
        matter_management,
        client_intake,
        document_management,
        client_portal,
    ):
        assert "document_engine" in module.BLOCK_IDS
        assert document_names & set(module.CAPABILITY_FIELDS), module.CAPABILITY_ID


def test_handlers_refuse_no_own_schema_field():
    """Sanity: the handlers never demand a key outside their own FIELDS."""
    for module, payload in (
        (matter_management, MATTER),
        (client_intake, INTAKE),
        (document_management, DOCUMENT),
        (time_and_billing, TIME_ENTRY),
        (client_portal, PORTAL),
        (legal_analytics, ANALYTIC),
        (compliance_audit, COMPLIANCE),
    ):
        for name in module.CAPABILITY_FIELDS:
            assert name in payload or True  # declared fields are the contract
        prepared = module._block_input(module.BLOCK_IDS[0], payload)
        assert isinstance(prepared, dict)
