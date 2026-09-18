"""v3: tenant corpus for grounded answers (app/retrieval.py).

Revision ID: 0003_corpus_documents
Revises: 0002_lifecycle_audit
Create Date: 2026-09-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_corpus_documents"
down_revision = "0002_lifecycle_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corpus_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("layer", sa.Text(), nullable=False),
        sa.Column("certified", sa.Integer(), nullable=False),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("corpus_documents")
