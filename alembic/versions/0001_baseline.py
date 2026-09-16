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
        "inventory_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("sku", sa.Text(), nullable=True),
        sa.Column("product_name", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("quantity_on_hand", sa.Integer(), nullable=True),
        sa.Column("reorder_point", sa.Integer(), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("supplier_name", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("movement_type", sa.Text(), nullable=True),
        sa.Column("last_counted_date", sa.Text(), nullable=True),
    )
    op.create_table(
        "sales_and_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("order_number", sa.Text(), nullable=True),
        sa.Column("customer_name", sa.Text(), nullable=True),
        sa.Column("customer_email", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("order_total", sa.Float(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=True),
        sa.Column("payment_status", sa.Text(), nullable=True),
        sa.Column("fulfilment_status", sa.Text(), nullable=True),
        sa.Column("order_date", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "customer_insights",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("customer_name", sa.Text(), nullable=True),
        sa.Column("customer_email", sa.Text(), nullable=True),
        sa.Column("segment", sa.Text(), nullable=True),
        sa.Column("lifetime_value", sa.Float(), nullable=True),
        sa.Column("orders_count", sa.Integer(), nullable=True),
        sa.Column("last_purchase_date", sa.Text(), nullable=True),
        sa.Column("loyalty_tier", sa.Text(), nullable=True),
        sa.Column("preferred_channel", sa.Text(), nullable=True),
        sa.Column("insight_summary", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
    )
    op.create_table(
        "analytics_dashboard",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("dashboard_name", sa.Text(), nullable=True),
        sa.Column("metric_name", sa.Text(), nullable=True),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("period_start", sa.Text(), nullable=True),
        sa.Column("period_end", sa.Text(), nullable=True),
        sa.Column("store_location", sa.Text(), nullable=True),
        sa.Column("widget_type", sa.Text(), nullable=True),
        sa.Column("report_format", sa.Text(), nullable=True),
        sa.Column("owner", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "supplier_and_purchasing",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("supplier_name", sa.Text(), nullable=True),
        sa.Column("supplier_email", sa.Text(), nullable=True),
        sa.Column("purchase_order_number", sa.Text(), nullable=True),
        sa.Column("sku", sa.Text(), nullable=True),
        sa.Column("quantity_ordered", sa.Integer(), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("order_date", sa.Text(), nullable=True),
        sa.Column("expected_date", sa.Text(), nullable=True),
        sa.Column("payment_terms", sa.Text(), nullable=True),
    )
    op.create_table(
        "omnichannel_integration",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("integration_name", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("external_order_id", sa.Text(), nullable=True),
        sa.Column("sync_direction", sa.Text(), nullable=True),
        sa.Column("sync_status", sa.Text(), nullable=True),
        sa.Column("sku", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("sync_at", sa.Text(), nullable=True),
        sa.Column("marketplace", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "compliance_and_audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("control_id", sa.Text(), nullable=True),
        sa.Column("regulation", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("evidence_ref", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True),
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
    op.drop_table('compliance_and_audit')
    op.drop_table('omnichannel_integration')
    op.drop_table('supplier_and_purchasing')
    op.drop_table('analytics_dashboard')
    op.drop_table('customer_insights')
    op.drop_table('sales_and_orders')
    op.drop_table('inventory_management')
