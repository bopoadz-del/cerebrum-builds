"""v1 domain tables from the capability specs.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-23
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
        "analytics_and_reporting",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("report_name", sa.Text(), nullable=True),
        sa.Column("metric_name", sa.Text(), nullable=True),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("period_start", sa.Text(), nullable=True),
        sa.Column("period_end", sa.Text(), nullable=True),
        sa.Column("appointments_count", sa.Integer(), nullable=True),
        sa.Column("revenue_total", sa.Float(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=True),
    )
    op.create_table(
        "appointment_scheduling",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("owner_name", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.Text(), nullable=True),
        sa.Column("appointment_type", sa.Text(), nullable=True),
        sa.Column("veterinarian", sa.Text(), nullable=True),
        sa.Column("room", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("reminder_channel", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "billing_and_invoicing",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("owner_name", sa.Text(), nullable=True),
        sa.Column("service_code", sa.Text(), nullable=True),
        sa.Column("invoice_total", sa.Float(), nullable=True),
        sa.Column("amount_paid", sa.Float(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("issued_on", sa.Text(), nullable=True),
        sa.Column("due_on", sa.Text(), nullable=True),
        sa.Column("payment_method", sa.Text(), nullable=True),
        sa.Column("attachment_path", sa.Text(), nullable=True),
    )
    op.create_table(
        "client_communication_and_reminders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("owner_name", sa.Text(), nullable=True),
        sa.Column("owner_email", sa.Text(), nullable=True),
        sa.Column("reminder_type", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.Text(), nullable=True),
        sa.Column("template_name", sa.Text(), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=True),
    )
    op.create_table(
        "clinical_visit_notes_and_treatment_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("visit_date", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("treatment_plan", sa.Text(), nullable=True),
        sa.Column("medication", sa.Text(), nullable=True),
        sa.Column("dosage_mg", sa.Float(), nullable=True),
        sa.Column("administration_route", sa.Text(), nullable=True),
        sa.Column("attachment_path", sa.Text(), nullable=True),
        sa.Column("prescription_notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "compliance_and_audit_trail",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("record_type", sa.Text(), nullable=True),
        sa.Column("subject_ref", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("reviewer", sa.Text(), nullable=True),
        sa.Column("reviewed_on", sa.Text(), nullable=True),
        sa.Column("retention_until", sa.Text(), nullable=True),
    )
    op.create_table(
        "patient_and_owner_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("species", sa.Text(), nullable=True),
        sa.Column("breed", sa.Text(), nullable=True),
        sa.Column("sex", sa.Text(), nullable=True),
        sa.Column("age_years", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("microchip_id", sa.Text(), nullable=True),
        sa.Column("owner_name", sa.Text(), nullable=True),
        sa.Column("owner_email", sa.Text(), nullable=True),
        sa.Column("owner_phone", sa.Text(), nullable=True),
        sa.Column("clinical_history", sa.Text(), nullable=True),
    )
    op.create_table(
        "vaccination_tracking",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("vaccine_type", sa.Text(), nullable=True),
        sa.Column("administered_on", sa.Text(), nullable=True),
        sa.Column("next_due_on", sa.Text(), nullable=True),
        sa.Column("lot_number", sa.Text(), nullable=True),
        sa.Column("administered_by", sa.Text(), nullable=True),
        sa.Column("reminder_channel", sa.Text(), nullable=True),
    )
    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Text(), nullable=False),
    )
    op.create_index("ix_rag_chunks_tenant", "rag_chunks", ["tenant_id"])
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
    op.drop_index("ix_rag_chunks_tenant", table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_table("idempotency")
    op.drop_table("work_queue")
    op.drop_table("vaccination_tracking")
    op.drop_table("patient_and_owner_records")
    op.drop_table("compliance_and_audit_trail")
    op.drop_table("clinical_visit_notes_and_treatment_plans")
    op.drop_table("client_communication_and_reminders")
    op.drop_table("billing_and_invoicing")
    op.drop_table("appointment_scheduling")
    op.drop_table("analytics_and_reporting")
