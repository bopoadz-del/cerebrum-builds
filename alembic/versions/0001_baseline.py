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
        "audit_trail",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("action_kind", sa.Text(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=True),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("attachment_path", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("audit", sa.Text(), nullable=True),
        sa.Column("capture", sa.Text(), nullable=True),
        sa.Column("evidence_verifier", sa.Text(), nullable=True),
        sa.Column("file_hasher", sa.Text(), nullable=True),
    )
    op.create_table(
        "fleet_registry",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("plate_number", sa.Text(), nullable=True),
        sa.Column("vin", sa.Text(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("vehicle_state", sa.Text(), nullable=True),
        sa.Column("mileage", sa.Integer(), nullable=True),
        sa.Column("service_history", sa.Text(), nullable=True),
        sa.Column("attachment_path", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("audit", sa.Text(), nullable=True),
        sa.Column("database", sa.Text(), nullable=True),
        sa.Column("storage", sa.Text(), nullable=True),
    )
    op.create_table(
        "invoicing_and_deposits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("invoice_number", sa.Text(), nullable=True),
        sa.Column("contract_reference", sa.Text(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.Column("amount_due", sa.Float(), nullable=True),
        sa.Column("deposit_held", sa.Float(), nullable=True),
        sa.Column("credit_note", sa.Text(), nullable=True),
        sa.Column("balance_due", sa.Float(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("analytics", sa.Text(), nullable=True),
        sa.Column("audit", sa.Text(), nullable=True),
        sa.Column("database", sa.Text(), nullable=True),
        sa.Column("workflow", sa.Text(), nullable=True),
    )
    op.create_table(
        "maintenance_scheduling",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("vehicle_reference", sa.Text(), nullable=True),
        sa.Column("schedule_kind", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Text(), nullable=True),
        sa.Column("due_mileage", sa.Integer(), nullable=True),
        sa.Column("workshop", sa.Text(), nullable=True),
        sa.Column("downtime_days", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
    )
    op.create_table(
        "multi_branch_rollup",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.Column("period", sa.Text(), nullable=True),
        sa.Column("fleet_utilisation", sa.Float(), nullable=True),
        sa.Column("revenue", sa.Float(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("profit", sa.Float(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("analytics", sa.Text(), nullable=True),
        sa.Column("dashboard", sa.Text(), nullable=True),
        sa.Column("estate_registry", sa.Text(), nullable=True),
        sa.Column("portfolio_rollup", sa.Text(), nullable=True),
    )
    op.create_table(
        "pricing_and_rate_cards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.Column("season", sa.Text(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("base_rate", sa.Float(), nullable=True),
        sa.Column("mileage_charge", sa.Float(), nullable=True),
        sa.Column("fuel_charge", sa.Float(), nullable=True),
        sa.Column("late_return_charge", sa.Float(), nullable=True),
        sa.Column("extras_charge", sa.Float(), nullable=True),
        sa.Column("deposit_amount", sa.Float(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("analytics", sa.Text(), nullable=True),
        sa.Column("audit", sa.Text(), nullable=True),
        sa.Column("formula_executor", sa.Text(), nullable=True),
        sa.Column("validation", sa.Text(), nullable=True),
    )
    op.create_table(
        "rental_contract_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("customer_name", sa.Text(), nullable=True),
        sa.Column("vehicle_reference", sa.Text(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.Column("pickup_date", sa.Text(), nullable=True),
        sa.Column("return_date", sa.Text(), nullable=True),
        sa.Column("extension_days", sa.Integer(), nullable=True),
        sa.Column("daily_rate", sa.Float(), nullable=True),
        sa.Column("deposit_amount", sa.Float(), nullable=True),
        sa.Column("damage_notes", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
    )
    op.create_table(
        "reporting_analytics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("metric", sa.Text(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.Column("period", sa.Text(), nullable=True),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("analytics", sa.Text(), nullable=True),
        sa.Column("dashboard", sa.Text(), nullable=True),
        sa.Column("memory", sa.Text(), nullable=True),
        sa.Column("vector_search", sa.Text(), nullable=True),
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
    op.drop_table("reporting_analytics")
    op.drop_table("rental_contract_management")
    op.drop_table("pricing_and_rate_cards")
    op.drop_table("multi_branch_rollup")
    op.drop_table("maintenance_scheduling")
    op.drop_table("invoicing_and_deposits")
    op.drop_table("fleet_registry")
    op.drop_table("audit_trail")
