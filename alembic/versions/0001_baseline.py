"""v1 domain tables from the capability specs.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_and_site_tracking",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("job_code", sa.Text(), nullable=True),
        sa.Column("job_name", sa.Text(), nullable=True),
        sa.Column("site_name", sa.Text(), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=True),
        sa.Column("work_front", sa.Text(), nullable=True),
        sa.Column("contract_value_aed", sa.Float(), nullable=True),
        sa.Column("progress_percent", sa.Float(), nullable=True),
        sa.Column("milestone", sa.Text(), nullable=True),
        sa.Column("milestone_due_date", sa.Text(), nullable=True),
        sa.Column("snag_open_count", sa.Integer(), nullable=True),
        sa.Column("variation_reference", sa.Text(), nullable=True),
        sa.Column("variation_status", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "commercials_and_valuations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("valuation_number", sa.Text(), nullable=True),
        sa.Column("job_code", sa.Text(), nullable=True),
        sa.Column("boq_item", sa.Text(), nullable=True),
        sa.Column("measured_quantity", sa.Float(), nullable=True),
        sa.Column("unit_rate_aed", sa.Float(), nullable=True),
        sa.Column("gross_value_aed", sa.Float(), nullable=True),
        sa.Column("retention_percent", sa.Float(), nullable=True),
        sa.Column("retention_aed", sa.Float(), nullable=True),
        sa.Column("vat_rate_percent", sa.Float(), nullable=True),
        sa.Column("vat_amount_aed", sa.Float(), nullable=True),
        sa.Column("certified_value_aed", sa.Float(), nullable=True),
        sa.Column("payment_status", sa.Text(), nullable=True),
        sa.Column("purchase_order", sa.Text(), nullable=True),
        sa.Column("po_party_type", sa.Text(), nullable=True),
        sa.Column("amount_due_aed", sa.Float(), nullable=True),
        sa.Column("due_on", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "document_qa_and_indexing",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("document_title", sa.Text(), nullable=True),
        sa.Column("document_type", sa.Text(), nullable=True),
        sa.Column("job_code", sa.Text(), nullable=True),
        sa.Column("revision", sa.Text(), nullable=True),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_sha256", sa.Text(), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "safety_and_compliance",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("job_code", sa.Text(), nullable=True),
        sa.Column("document_title", sa.Text(), nullable=True),
        sa.Column("method_statement_ref", sa.Text(), nullable=True),
        sa.Column("work_front", sa.Text(), nullable=True),
        sa.Column("checklist_item", sa.Text(), nullable=True),
        sa.Column("checklist_state", sa.Text(), nullable=True),
        sa.Column("readiness_gate", sa.Text(), nullable=True),
        sa.Column("incident_type", sa.Text(), nullable=True),
        sa.Column("incident_date", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "progress_cost_dashboard",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("report_date", sa.Text(), nullable=True),
        sa.Column("job_code", sa.Text(), nullable=True),
        sa.Column("progress_percent", sa.Float(), nullable=True),
        sa.Column("certified_value_aed", sa.Float(), nullable=True),
        sa.Column("cost_to_date_aed", sa.Float(), nullable=True),
        sa.Column("variations_pending", sa.Integer(), nullable=True),
        sa.Column("snags_open", sa.Integer(), nullable=True),
        sa.Column("payments_due_aed", sa.Float(), nullable=True),
        sa.Column("margin_percent", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.create_table(
        "automation_reminders_escalation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("job_code", sa.Text(), nullable=True),
        sa.Column("reminder_type", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Text(), nullable=True),
        sa.Column("threshold_count", sa.Integer(), nullable=True),
        sa.Column("actual_count", sa.Integer(), nullable=True),
        sa.Column("escalation_state", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("recipient_email", sa.Text(), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("schedule", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.create_table(
        "audit_and_access_control",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("actor_name", sa.Text(), nullable=True),
        sa.Column("actor_role", sa.Text(), nullable=True),
        sa.Column("action_type", sa.Text(), nullable=True),
        sa.Column("entity_name", sa.Text(), nullable=True),
        sa.Column("entity_reference", sa.Text(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("approval_state", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "team_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("recipient_email", sa.Text(), nullable=True),
        sa.Column("recipient_role", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("notification_type", sa.Text(), nullable=True),
        sa.Column("related_reference", sa.Text(), nullable=True),
        sa.Column("send_at", sa.Text(), nullable=True),
        sa.Column("delivery_state", sa.Text(), nullable=True),
    )
    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Text(), nullable=False),
    )
    op.create_table(
        "work_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("capability_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
    )
    op.create_table(
        "idempotency",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("entity", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("idempotency")
    op.drop_table("work_queue")
    op.drop_table("rag_chunks")
    op.drop_table("team_notifications")
    op.drop_table("audit_and_access_control")
    op.drop_table("automation_reminders_escalation")
    op.drop_table("progress_cost_dashboard")
    op.drop_table("safety_and_compliance")
    op.drop_table("document_qa_and_indexing")
    op.drop_table("commercials_and_valuations")
    op.drop_table("job_and_site_tracking")
