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
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=True),
        sa.Column("change_type", sa.Text(), nullable=True),
        sa.Column("subject_capability", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
    )
    op.create_table(
        "checkin_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("guest_name", sa.Text(), nullable=True),
        sa.Column("room_number", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("recipient", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
    )
    op.create_table(
        "daily_checkin_summary",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("summary_date", sa.Text(), nullable=True),
        sa.Column("arrivals_count", sa.Integer(), nullable=True),
        sa.Column("occupancy_percent", sa.Float(), nullable=True),
        sa.Column("no_show_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
    )
    op.create_table(
        "guest_notes_and_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("guest_name", sa.Text(), nullable=True),
        sa.Column("room_number", sa.Text(), nullable=True),
        sa.Column("preference", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
    )
    op.create_table(
        "record_checkin",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("guest_name", sa.Text(), nullable=True),
        sa.Column("room_number", sa.Text(), nullable=True),
        sa.Column("nights", sa.Integer(), nullable=True),
        sa.Column("arrival_time", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
    )
    op.create_table(
        "room_availability_check",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("room_number", sa.Text(), nullable=True),
        sa.Column("check_in_date", sa.Text(), nullable=True),
        sa.Column("check_out_date", sa.Text(), nullable=True),
        sa.Column("is_available", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
    )
    op.create_table(
        "todays_arrivals_board",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("arrival_date", sa.Text(), nullable=True),
        sa.Column("guest_name", sa.Text(), nullable=True),
        sa.Column("room_number", sa.Text(), nullable=True),
        sa.Column("arrived", sa.Integer(), nullable=True),
        sa.Column("arrivals_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
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
    op.drop_table("todays_arrivals_board")
    op.drop_table("room_availability_check")
    op.drop_table("record_checkin")
    op.drop_table("guest_notes_and_preferences")
    op.drop_table("daily_checkin_summary")
    op.drop_table("checkin_notifications")
    op.drop_table("audit_trail")
