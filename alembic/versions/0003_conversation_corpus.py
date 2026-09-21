"""Work queue, idempotency keys and the project-sheet corpus.

Revision ID: 0003_conversation_corpus
Revises: 0002_lifecycle_audit
Create Date: 2026-09-21

Three tables the capability tables do not carry:

* ``work_queue`` — the durable dial list. A lead's turn to be dialled is a
  row, so a restart loses no queued call, and a claimed item carries its own
  ``tenant_id`` so processing never runs as the wrong brokerage.
* ``idempotency`` — a repeated request with the same key returns the row it
  already made instead of dialling the same person twice.
* ``rag_documents`` / ``rag_chunks`` — ingested PSI project sheets and their
  chunks, tenant-scoped. A second brokerage's price list is a different row
  set, not a rebuild.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_conversation_corpus"
down_revision = "0002_lifecycle_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("capability_id", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text()),
        sa.Column("attempts", sa.Integer()),
        sa.Column("result", sa.Text()),
        sa.Column("claimed_at", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_work_queue_tenant_status", "work_queue", ["tenant_id", "status"])

    op.create_table(
        "idempotency",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("entity", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_idempotency_tenant_key", "idempotency", ["tenant_id", "key"])

    op.create_table(
        "rag_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("project_tag", sa.Text()),
        sa.Column("source", sa.Text()),
        sa.Column("certified", sa.Integer()),
        sa.Column("content", sa.Text()),
        sa.Column("digest", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_rag_documents_tenant_project", "rag_documents", ["tenant_id", "project_tag"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=False),
        sa.Column("project_tag", sa.Text()),
        sa.Column("ordinal", sa.Integer()),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("certified", sa.Integer()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_rag_chunks_tenant_project", "rag_chunks", ["tenant_id", "project_tag"])


def downgrade() -> None:
    op.drop_index("ix_rag_chunks_tenant_project", table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_index("ix_rag_documents_tenant_project", table_name="rag_documents")
    op.drop_table("rag_documents")
    op.drop_index("ix_idempotency_tenant_key", table_name="idempotency")
    op.drop_table("idempotency")
    op.drop_index("ix_work_queue_tenant_status", table_name="work_queue")
    op.drop_table("work_queue")
