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
        "patient_visit_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("tooth", sa.Text(), nullable=True),
        sa.Column("procedure", sa.Text(), nullable=True),
        sa.Column("fee", sa.Float(), nullable=True),
        sa.Column("visit_date", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "appointment_scheduling",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("patient_email", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("chair_room", sa.Text(), nullable=True),
        sa.Column("appointment_type", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("reminder_channel", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "todays_appointment_list",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("list_date", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("procedure", sa.Text(), nullable=True),
        sa.Column("appointment_time", sa.Text(), nullable=True),
        sa.Column("appointment_status", sa.Text(), nullable=True),
        sa.Column("chair_room", sa.Text(), nullable=True),
    )
    op.create_table(
        "day_before_email_reminders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("patient_email", sa.Text(), nullable=True),
        sa.Column("reminder_date", sa.Text(), nullable=True),
        sa.Column("appointment_at", sa.Text(), nullable=True),
        sa.Column("reminder_channel", sa.Text(), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("delivery_state", sa.Text(), nullable=True),
    )
    op.create_table(
        "patient_directory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("patient_email", sa.Text(), nullable=True),
        sa.Column("patient_phone", sa.Text(), nullable=True),
        sa.Column("date_of_birth", sa.Text(), nullable=True),
        sa.Column("primary_provider", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "clinical_history_search",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("tooth", sa.Text(), nullable=True),
        sa.Column("procedure", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("visit_date", sa.Text(), nullable=True),
        sa.Column("date_from", sa.Text(), nullable=True),
        sa.Column("date_to", sa.Text(), nullable=True),
        sa.Column("search_notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "role_based_access",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_document", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("staff_name", sa.Text(), nullable=True),
        sa.Column("staff_email", sa.Text(), nullable=True),
        sa.Column("staff_role", sa.Text(), nullable=True),
        sa.Column("permission_scope", sa.Text(), nullable=True),
        sa.Column("active_from", sa.Text(), nullable=True),
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
    op.drop_table("role_based_access")
    op.drop_table("clinical_history_search")
    op.drop_table("patient_directory")
    op.drop_table("day_before_email_reminders")
    op.drop_table("todays_appointment_list")
    op.drop_table("appointment_scheduling")
    op.drop_table("patient_visit_records")
