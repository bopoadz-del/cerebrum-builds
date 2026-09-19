"""Lifecycle tables: audit trail, work queue, idempotency keys.

Revision ID: 0002_lifecycle_audit
Revises: 0001_baseline
Create Date: 2026-09-19

Written by the factory WRITER role (codewhale exec)

The platform's own bookkeeping tables. They are separate from the capability
entities so a capability's round-trip is judged on its own table.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_lifecycle_audit"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lifecycle_audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "work_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "idempotency",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="local"),
        sa.Column("capability_id", sa.Text(), nullable=True),
        sa.Column("record_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("idempotency")
    op.drop_table("work_queue")
    op.drop_table("lifecycle_audit")
