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
        "auto_assignment",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("complaint_reference", sa.Text(), nullable=True),
        sa.Column("school", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("required_trade", sa.Text(), nullable=True),
        sa.Column("required_skill", sa.Text(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=True),
        sa.Column("assigned_to", sa.Text(), nullable=True),
        sa.Column("assigned_role", sa.Text(), nullable=True),
        sa.Column("assignment_mode", sa.Text(), nullable=True),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("workload_score", sa.Integer(), nullable=True),
        sa.Column("queue_position", sa.Integer(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "booking_system_integration",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("integration", sa.Text(), nullable=True),
        sa.Column("mode", sa.Text(), nullable=True),
        sa.Column("booking_reference", sa.Text(), nullable=True),
        sa.Column("school", sa.Text(), nullable=True),
        sa.Column("facility", sa.Text(), nullable=True),
        sa.Column("slot_start", sa.Text(), nullable=True),
        sa.Column("slot_end", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.Text(), nullable=True),
        sa.Column("sync_state", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "complaints_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("school", sa.Text(), nullable=True),
        sa.Column("site_code", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("raised_by", sa.Text(), nullable=True),
        sa.Column("raised_by_role", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.Text(), nullable=True),
        sa.Column("logged_by", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.Text(), nullable=True),
        sa.Column("assignment_mode", sa.Text(), nullable=True),
        sa.Column("reported_at", sa.Text(), nullable=True),
        sa.Column("due_at", sa.Text(), nullable=True),
        sa.Column("sla_hours", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("work_order_reference", sa.Text(), nullable=True),
    )
    op.create_table(
        "erp_integration",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("integration", sa.Text(), nullable=True),
        sa.Column("mode", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.Text(), nullable=True),
        sa.Column("direction", sa.Text(), nullable=True),
        sa.Column("external_reference", sa.Text(), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("sync_state", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "management_dashboards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("school", sa.Text(), nullable=True),
        sa.Column("period", sa.Text(), nullable=True),
        sa.Column("complaints_open", sa.Integer(), nullable=True),
        sa.Column("complaints_in_progress", sa.Integer(), nullable=True),
        sa.Column("complaints_closed", sa.Integer(), nullable=True),
        sa.Column("jobs_in_progress", sa.Integer(), nullable=True),
        sa.Column("sla_breaches", sa.Integer(), nullable=True),
        sa.Column("sla_compliance_pct", sa.Float(), nullable=True),
        sa.Column("avg_closure_hours", sa.Float(), nullable=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "reporting",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("report_type", sa.Text(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("school", sa.Text(), nullable=True),
        sa.Column("period_start", sa.Text(), nullable=True),
        sa.Column("period_end", sa.Text(), nullable=True),
        sa.Column("complaints_total", sa.Integer(), nullable=True),
        sa.Column("closed_total", sa.Integer(), nullable=True),
        sa.Column("avg_closure_hours", sa.Float(), nullable=True),
        sa.Column("sla_compliance_pct", sa.Float(), nullable=True),
        sa.Column("top_category", sa.Text(), nullable=True),
        sa.Column("busiest_school", sa.Text(), nullable=True),
        sa.Column("recipients", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "role_based_access",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("principal", sa.Text(), nullable=True),
        sa.Column("principal_email", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("school", sa.Text(), nullable=True),
        sa.Column("access_scope", sa.Text(), nullable=True),
        sa.Column("permissions", sa.Text(), nullable=True),
        sa.Column("granted_by", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Text(), nullable=True),
        sa.Column("last_review_at", sa.Text(), nullable=True),
        sa.Column("active", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "workforce_management",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("school", sa.Text(), nullable=True),
        sa.Column("team_name", sa.Text(), nullable=True),
        sa.Column("team_type", sa.Text(), nullable=True),
        sa.Column("trade", sa.Text(), nullable=True),
        sa.Column("shift", sa.Text(), nullable=True),
        sa.Column("headcount", sa.Integer(), nullable=True),
        sa.Column("lead_name", sa.Text(), nullable=True),
        sa.Column("lead_email", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.Text(), nullable=True),
        sa.Column("active", sa.Integer(), nullable=True),
        sa.Column("open_jobs", sa.Integer(), nullable=True),
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
    op.drop_table("workforce_management")
    op.drop_table("role_based_access")
    op.drop_table("reporting")
    op.drop_table("management_dashboards")
    op.drop_table("erp_integration")
    op.drop_table("complaints_management")
    op.drop_table("booking_system_integration")
    op.drop_table("auto_assignment")
