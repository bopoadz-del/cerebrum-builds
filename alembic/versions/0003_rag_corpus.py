"""v3 corpus tables: the property's own documents and their chunks.

Revision ID: 0003_rag_corpus
Revises: 0002_lifecycle_audit
Create Date: 2026-09-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_rag_corpus"
down_revision = "0002_lifecycle_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_document",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=True),
        sa.Column("authority_label", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "rag_chunk",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("terms", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("rag_chunk")
    op.drop_table("rag_document")
