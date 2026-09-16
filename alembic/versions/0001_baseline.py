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
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("pet_name", sa.Text(), nullable=True),
        sa.Column("owner_name", sa.Text(), nullable=True),
        sa.Column("veterinarian", sa.Text(), nullable=True),
        sa.Column("appointment_date", sa.Text(), nullable=True),
        sa.Column("appointment_time", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("visit_reason", sa.Text(), nullable=True),
        sa.Column("room", sa.Text(), nullable=True),
        sa.Column("appointment_status", sa.Text(), nullable=True),
    )
    op.create_table(
        "audit_trail",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=True),
        sa.Column("entity_name", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=True),
        sa.Column("actor_role", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "billing_invoicing",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("invoice_number", sa.Text(), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=True),
        sa.Column("pet_name", sa.Text(), nullable=True),
        sa.Column("line_items", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=True),
        sa.Column("tax_rate", sa.Float(), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column("payment_status", sa.Text(), nullable=True),
        sa.Column("payment_method", sa.Text(), nullable=True),
        sa.Column("invoice_date", sa.Text(), nullable=True),
        sa.Column("attachment_path", sa.Text(), nullable=True),
    )
    op.create_table(
        "clinic_analytics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("metric_name", sa.Text(), nullable=True),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("period", sa.Text(), nullable=True),
        sa.Column("period_start", sa.Text(), nullable=True),
        sa.Column("period_end", sa.Text(), nullable=True),
        sa.Column("dimension", sa.Text(), nullable=True),
    )
    op.create_table(
        "inventory_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("item_name", sa.Text(), nullable=True),
        sa.Column("sku", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("reorder_level", sa.Integer(), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("supplier", sa.Text(), nullable=True),
        sa.Column("expiry_date", sa.Text(), nullable=True),
    )
    op.create_table(
        "patient_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("pet_name", sa.Text(), nullable=True),
        sa.Column("species", sa.Text(), nullable=True),
        sa.Column("breed", sa.Text(), nullable=True),
        sa.Column("owner_name", sa.Text(), nullable=True),
        sa.Column("owner_email", sa.Text(), nullable=True),
        sa.Column("owner_phone", sa.Text(), nullable=True),
        sa.Column("date_of_birth", sa.Text(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("vaccination_status", sa.Text(), nullable=True),
        sa.Column("allergies", sa.Text(), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "role_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("role_name", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("permissions", sa.Text(), nullable=True),
        sa.Column("access_level", sa.Text(), nullable=True),
        sa.Column("department", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Integer(), nullable=True),
    )
    op.create_table(
        "treatment_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("pet_name", sa.Text(), nullable=True),
        sa.Column("veterinarian", sa.Text(), nullable=True),
        sa.Column("treatment_type", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("procedure_notes", sa.Text(), nullable=True),
        sa.Column("medication", sa.Text(), nullable=True),
        sa.Column("dosage", sa.Text(), nullable=True),
        sa.Column("treatment_date", sa.Text(), nullable=True),
        sa.Column("follow_up_date", sa.Text(), nullable=True),
        sa.Column("attachment_path", sa.Text(), nullable=True),
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
    op.drop_table("treatment_management")
    op.drop_table("role_management")
    op.drop_table("patient_records")
    op.drop_table("inventory_management")
    op.drop_table("clinic_analytics")
    op.drop_table("billing_invoicing")
    op.drop_table("audit_trail")
    op.drop_table("appointment_scheduling")
