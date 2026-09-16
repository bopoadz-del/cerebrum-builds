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
        "client_intake",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=True),
        sa.Column("client_email", sa.Text(), nullable=True),
        sa.Column("client_phone", sa.Text(), nullable=True),
        sa.Column("matter_type", sa.Text(), nullable=True),
        sa.Column("referral_source", sa.Text(), nullable=True),
        sa.Column("conflict_check", sa.Text(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("estimated_fee", sa.Float(), nullable=True),
        sa.Column("retainer_amount", sa.Float(), nullable=True),
        sa.Column("document_path", sa.Text(), nullable=True),
        sa.Column("intake_date", sa.Text(), nullable=True),
    )
    op.create_table(
        "client_portal",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=True),
        sa.Column("client_email", sa.Text(), nullable=True),
        sa.Column("matter_number", sa.Text(), nullable=True),
        sa.Column("portal_access_level", sa.Text(), nullable=True),
        sa.Column("unread_messages", sa.Integer(), nullable=True),
        sa.Column("shared_documents", sa.Integer(), nullable=True),
        sa.Column("message_subject", sa.Text(), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.Text(), nullable=True),
        sa.Column("document_path", sa.Text(), nullable=True),
    )
    op.create_table(
        "compliance_audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("control_id", sa.Text(), nullable=True),
        sa.Column("framework", sa.Text(), nullable=True),
        sa.Column("regulation", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=True),
        sa.Column("actor_role", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("evidence_ref", sa.Text(), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "document_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("document_title", sa.Text(), nullable=True),
        sa.Column("document_type", sa.Text(), nullable=True),
        sa.Column("matter_number", sa.Text(), nullable=True),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("confidentiality", sa.Text(), nullable=True),
        sa.Column("document_owner", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "legal_analytics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("metric_name", sa.Text(), nullable=True),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("benchmark_value", sa.Float(), nullable=True),
        sa.Column("practice_area", sa.Text(), nullable=True),
        sa.Column("dimension", sa.Text(), nullable=True),
        sa.Column("period_start", sa.Text(), nullable=True),
        sa.Column("period_end", sa.Text(), nullable=True),
        sa.Column("source_matter", sa.Text(), nullable=True),
    )
    op.create_table(
        "matter_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("matter_number", sa.Text(), nullable=True),
        sa.Column("matter_title", sa.Text(), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=True),
        sa.Column("client_email", sa.Text(), nullable=True),
        sa.Column("practice_area", sa.Text(), nullable=True),
        sa.Column("responsible_attorney", sa.Text(), nullable=True),
        sa.Column("matter_stage", sa.Text(), nullable=True),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("opened_date", sa.Text(), nullable=True),
        sa.Column("deadline_date", sa.Text(), nullable=True),
        sa.Column("billing_type", sa.Text(), nullable=True),
        sa.Column("document_path", sa.Text(), nullable=True),
    )
    op.create_table(
        "time_and_billing",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("timekeeper", sa.Text(), nullable=True),
        sa.Column("matter_number", sa.Text(), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=True),
        sa.Column("client_email", sa.Text(), nullable=True),
        sa.Column("activity_date", sa.Text(), nullable=True),
        sa.Column("hours", sa.Float(), nullable=True),
        sa.Column("hourly_rate", sa.Float(), nullable=True),
        sa.Column("billable_amount", sa.Float(), nullable=True),
        sa.Column("invoice_number", sa.Text(), nullable=True),
        sa.Column("payment_status", sa.Text(), nullable=True),
        sa.Column("narrative", sa.Text(), nullable=True),
    )
    op.create_table(
        "work_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("capability_id", sa.Text(), nullable=False),
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
    op.drop_table("time_and_billing")
    op.drop_table("matter_management")
    op.drop_table("legal_analytics")
    op.drop_table("document_management")
    op.drop_table("compliance_audit")
    op.drop_table("client_portal")
    op.drop_table("client_intake")
