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
        "appointment_scheduling",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
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
        sa.Column("appointment_status", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "clinic_dashboard",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("dashboard_date", sa.Text(), nullable=True),
        sa.Column("appointments_today", sa.Integer(), nullable=True),
        sa.Column("patients_seen", sa.Integer(), nullable=True),
        sa.Column("outstanding_invoices", sa.Integer(), nullable=True),
        sa.Column("recalls_due", sa.Integer(), nullable=True),
        sa.Column("chair_utilisation", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.create_table(
        "invoicing",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("invoice_number", sa.Text(), nullable=True),
        sa.Column("treatment_code", sa.Text(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("tax_rate", sa.Float(), nullable=True),
        sa.Column("total_due", sa.Float(), nullable=True),
        sa.Column("payment_status", sa.Text(), nullable=True),
        sa.Column("issued_on", sa.Text(), nullable=True),
        sa.Column("due_on", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("attachment_path", sa.Text(), nullable=True),
    )
    op.create_table(
        "patient_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("patient_email", sa.Text(), nullable=True),
        sa.Column("patient_phone", sa.Text(), nullable=True),
        sa.Column("date_of_birth", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("medical_history", sa.Text(), nullable=True),
        sa.Column("dental_history", sa.Text(), nullable=True),
        sa.Column("insurance_provider", sa.Text(), nullable=True),
        sa.Column("insurance_member_id", sa.Text(), nullable=True),
        sa.Column("primary_provider", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "recall_reminders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("patient_email", sa.Text(), nullable=True),
        sa.Column("recall_interval_months", sa.Integer(), nullable=True),
        sa.Column("last_visit_date", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Text(), nullable=True),
        sa.Column("reminder_type", sa.Text(), nullable=True),
        sa.Column("reminder_channel", sa.Text(), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("delivery_state", sa.Text(), nullable=True),
    )
    op.create_table(
        "staff_roles_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("staff_name", sa.Text(), nullable=True),
        sa.Column("staff_email", sa.Text(), nullable=True),
        sa.Column("staff_role", sa.Text(), nullable=True),
        sa.Column("permission_scope", sa.Text(), nullable=True),
        sa.Column("active_from", sa.Text(), nullable=True),
        sa.Column("active", sa.Integer(), nullable=True),
    )
    op.create_table(
        "treatment_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=True),
        sa.Column("tooth", sa.Text(), nullable=True),
        sa.Column("procedure", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("treatment_date", sa.Text(), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("follow_up_date", sa.Text(), nullable=True),
        sa.Column("attachment_name", sa.Text(), nullable=True),
        sa.Column("attachment_path", sa.Text(), nullable=True),
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
    op.drop_table("treatment_records")
    op.drop_table("staff_roles_permissions")
    op.drop_table("recall_reminders")
    op.drop_table("patient_records")
    op.drop_table("invoicing")
    op.drop_table("clinic_dashboard")
    op.drop_table("appointment_scheduling")
