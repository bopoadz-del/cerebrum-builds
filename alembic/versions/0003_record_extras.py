"""v3 schema change: record_extras side table (up and down).

The store entity carries the capability's own columns. A caller may still
hand the route a key the entity does not declare (a field the spec has not
caught up with, or a composite the front desk pasted in). Round-tripping
that key is the difference between "persisted nothing" and persistence:
save() records the undeclared keys here and get()/list_all()/query() merge
them back, so a read returns exactly what a write was given.

Revision ID: 0003_record_extras
Revises: 0002_lifecycle_audit
Create Date: 2026-09-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_record_extras"
down_revision = "0002_lifecycle_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "record_extras",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("record_extras")
