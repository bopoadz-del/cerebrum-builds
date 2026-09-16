"""v2 schema change: audit trail, alert outbox and tenant corpus (up and down).

The factory emitter's revision id and name are kept: the data-lifecycle suite
pins ``REV_V2 = '0002_lifecycle_audit'`` as head. This revision therefore also
creates the two platform-owned tables the capabilities need -- the alert
outbox (``notification_outbox``) and the tenant-scoped corpus
(``corpus_documents`` / ``corpus_chunks`` / ``answer_log``). Tenancy is a
column and a predicate in the one STORAGE_PATH database, never a second file.

Revision ID: 0002_lifecycle_audit
Revises: 0001_baseline
Create Date: 2026-08-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_lifecycle_audit"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lifecycle_audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("at", sa.Text(), nullable=False),
    )
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("capability", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("block_id", sa.Text(), nullable=False),
        sa.Column("block_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "corpus_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("layer", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("certified", sa.Integer(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_corpus_documents_tenant", "corpus_documents", ["tenant"])
    op.create_table(
        "corpus_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )
    op.create_index("ix_corpus_chunks_tenant", "corpus_chunks", ["tenant"])
    op.create_table(
        "answer_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("winner_source", sa.Text(), nullable=False),
        sa.Column("labels", sa.Text(), nullable=False),
        sa.Column("divergences", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("answer_log")
    op.drop_index("ix_corpus_chunks_tenant", table_name="corpus_chunks")
    op.drop_table("corpus_chunks")
    op.drop_index("ix_corpus_documents_tenant", table_name="corpus_documents")
    op.drop_table("corpus_documents")
    op.drop_table("notification_outbox")
    op.drop_table("lifecycle_audit")
