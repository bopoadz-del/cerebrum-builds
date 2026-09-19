"""Baseline schema: one table per capability, tenant-scoped.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-19

Written by the factory WRITER role (codewhale exec)

Every capability gets its own table named by its ``spec.entity`` (the
capability id) and ``app/store.COLUMNS`` reads the same names, so a capability
with no migrated table fails loudly instead of writing nowhere.

The calls are written out one per entity rather than looped: the platform's own
schema register and every reviewer read this file, and a name built from a loop
variable is not a name they can see.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_inventory_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("created_at", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text()),
        sa.Column("shop_code", sa.Text()),
        sa.Column("item_code", sa.Text()),
        sa.Column("item_name", sa.Text()),
        sa.Column("quantity_on_hand", sa.Integer()),
        sa.Column("reorder_threshold", sa.Integer()),
        sa.Column("unit", sa.Text()),
        sa.Column("movement_type", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_table(
        "product_pricing",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("created_at", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text()),
        sa.Column("product_code", sa.Text()),
        sa.Column("product_name", sa.Text()),
        sa.Column("shop_code", sa.Text()),
        sa.Column("unit_cost", sa.Float()),
        sa.Column("margin_percent", sa.Float()),
        sa.Column("unit_price", sa.Float()),
        sa.Column("price_list_version", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_table(
        "delivery_dispatch_tracking",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("created_at", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text()),
        sa.Column("order_code", sa.Text()),
        sa.Column("shop_code", sa.Text()),
        sa.Column("driver_code", sa.Text()),
        sa.Column("vehicle_code", sa.Text()),
        sa.Column("vehicle_type", sa.Text()),
        sa.Column("delivery_address", sa.Text()),
        sa.Column("scheduled_at", sa.Text()),
        sa.Column("delivery_state", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_table(
        "fleet_cost_tracking",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("created_at", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text()),
        sa.Column("vehicle_code", sa.Text()),
        sa.Column("vehicle_type", sa.Text()),
        sa.Column("cost_category", sa.Text()),
        sa.Column("amount", sa.Float()),
        sa.Column("distance_km", sa.Float()),
        sa.Column("incurred_date", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_table(
        "management_reporting_dashboard",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("created_at", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text()),
        sa.Column("metric_name", sa.Text()),
        sa.Column("metric_value", sa.Float()),
        sa.Column("shop_code", sa.Text()),
        sa.Column("reporting_period", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_table(
        "user_roles_workforce",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("created_at", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text()),
        sa.Column("user_name", sa.Text()),
        sa.Column("user_email", sa.Text()),
        sa.Column("role", sa.Text()),
        sa.Column("shop_code", sa.Text()),
        sa.Column("shift", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_table(
        "document_knowledge_qa",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("created_at", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text()),
        sa.Column("document_title", sa.Text()),
        sa.Column("document_type", sa.Text()),
        sa.Column("source_path", sa.Text()),
        sa.Column("question", sa.Text()),
        sa.Column("answer", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_table(
        "procedures_readiness_and_audit_trail",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("created_at", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text()),
        sa.Column("procedure_code", sa.Text()),
        sa.Column("procedure_title", sa.Text()),
        sa.Column("shop_code", sa.Text()),
        sa.Column("checklist", sa.Text()),
        sa.Column("due_date", sa.Text()),
        sa.Column("actor", sa.Text()),
        sa.Column("event_type", sa.Text()),
        sa.Column("evidence_path", sa.Text()),
        sa.Column("content_hash", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.Text()),
    )

def downgrade() -> None:
    op.drop_table("procedures_readiness_and_audit_trail")
    op.drop_table("document_knowledge_qa")
    op.drop_table("user_roles_workforce")
    op.drop_table("management_reporting_dashboard")
    op.drop_table("fleet_cost_tracking")
    op.drop_table("delivery_dispatch_tracking")
    op.drop_table("product_pricing")
    op.drop_table("stock_inventory_management")
