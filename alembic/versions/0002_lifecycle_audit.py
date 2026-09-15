"""lifecycle audit table for S10 schema-change drill

Revision ID: 0002_lifecycle_audit
Revises: 0001_baseline
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_lifecycle_audit"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lifecycle_audit",
        sa.Column("pk", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("lifecycle_audit")
