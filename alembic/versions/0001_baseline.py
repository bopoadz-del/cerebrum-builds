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
        "document_and_knowledge_answers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("document_kind", sa.Text(), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("document_text", sa.Text(), nullable=True),
        sa.Column("attachment_path", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("source_document", sa.Text(), nullable=True),
        sa.Column("authority_label", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "external_integration_adapter",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("system", sa.Text(), nullable=True),
        sa.Column("resource", sa.Text(), nullable=True),
        sa.Column("direction", sa.Text(), nullable=True),
        sa.Column("payload_format", sa.Text(), nullable=True),
        sa.Column("endpoint_url", sa.Text(), nullable=True),
        sa.Column("records_seen", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "front_desk_and_guest_stay",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("guest_name", sa.Text(), nullable=True),
        sa.Column("room_number", sa.Text(), nullable=True),
        sa.Column("arrival_date", sa.Text(), nullable=True),
        sa.Column("departure_date", sa.Text(), nullable=True),
        sa.Column("guests_count", sa.Integer(), nullable=True),
        sa.Column("stay_status", sa.Text(), nullable=True),
        sa.Column("folio_currency", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "guest_engagement_and_segmentation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("guest_name", sa.Text(), nullable=True),
        sa.Column("recency_days", sa.Integer(), nullable=True),
        sa.Column("frequency", sa.Integer(), nullable=True),
        sa.Column("monetary", sa.Float(), nullable=True),
        sa.Column("segment", sa.Text(), nullable=True),
        sa.Column("delivery_channel", sa.Text(), nullable=True),
        sa.Column("offer_code", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "housekeeping_and_maintenance",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("work_type", sa.Text(), nullable=True),
        sa.Column("room_number", sa.Text(), nullable=True),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.Text(), nullable=True),
        sa.Column("work_status", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "operations_billing",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("setting", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("folio_reference", sa.Text(), nullable=True),
        sa.Column("charge_type", sa.Text(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("tax_rate_percent", sa.Float(), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "operations_oversight_dashboard",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("dashboard_name", sa.Text(), nullable=True),
        sa.Column("widget", sa.Text(), nullable=True),
        sa.Column("window_days", sa.Integer(), nullable=True),
        sa.Column("operator_role", sa.Text(), nullable=True),
        sa.Column("occupancy_percent", sa.Float(), nullable=True),
        sa.Column("open_work_orders", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "property_and_room_registry",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("property_name", sa.Text(), nullable=True),
        sa.Column("building", sa.Text(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("room_number", sa.Text(), nullable=True),
        sa.Column("room_type", sa.Text(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("room_status", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.drop_table("property_and_room_registry")
    op.drop_table("operations_oversight_dashboard")
    op.drop_table("operations_billing")
    op.drop_table("housekeeping_and_maintenance")
    op.drop_table("guest_engagement_and_segmentation")
    op.drop_table("front_desk_and_guest_stay")
    op.drop_table("external_integration_adapter")
    op.drop_table("document_and_knowledge_answers")
