"""baseline capability entities

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

ENTITIES = (
    "airport_readiness",
    "operational_dashboard",
    "ground_workflow_coordination",
    "regulatory_document_control",
    "incident_evidence_tracking",
    "flight_event_orchestration",
    "airport_knowledge_assistant",
)


def upgrade() -> None:
    for entity in ENTITIES:
        op.create_table(
            entity,
            sa.Column("pk", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("reference", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    for entity in reversed(ENTITIES):
        op.drop_table(entity)
