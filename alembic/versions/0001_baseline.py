"""baseline capability entities

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

ENTITIES = (
    "aviation_core",
    "audit",
    "dashboard",
    "portfolio_program_governance",
    "hybrid_delivery_management",
    "integrated_planning_scheduling_milestones",
    "demand_prioritization_capacity_alignment",
    "budget_financial_guardrails_value_realization",
    "delivery_kpi_adoption_analytics",
    "erp_oracle_integration",
    "privacy_compliance_evidence",
    "governance_continuous_improvement",
    "airline_ops_portfolio_context",
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
