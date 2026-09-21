"""CallOps baseline: one table per capability.

Written by the factory WRITER role (codewhale exec)

One op.create_table per entity. Every table carries tenant_id (tenancy is
resolved from the authenticated principal, never the payload) and one
column per declared field. The schema is this revision and nothing else.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None



def upgrade_lead_intake_and_dial_queue() -> None:
    op.create_table(
        "lead_intake_and_dial_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("lead_name", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("project_tag", sa.String(), nullable=True),
        sa.Column("source_file", sa.String(), nullable=True),
        sa.Column("call_window", sa.String(), nullable=True),
        sa.Column("daily_call_cap", sa.Integer(), nullable=True),
        sa.Column("concurrency", sa.Integer(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=True),
        sa.Column("retry_backoff_minutes", sa.Integer(), nullable=True),
        sa.Column("queue_status", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_call_state_machine() -> None:
    op.create_table(
        "call_state_machine",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("call_sid", sa.String(), nullable=True),
        sa.Column("lead_name", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("current_state", sa.String(), nullable=True),
        sa.Column("previous_state", sa.String(), nullable=True),
        sa.Column("call_window", sa.String(), nullable=True),
        sa.Column("window_state", sa.String(), nullable=True),
        sa.Column("transition_event", sa.String(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_project_knowledge_grounding() -> None:
    op.create_table(
        "project_knowledge_grounding",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("project_tag", sa.String(), nullable=True),
        sa.Column("claim_type", sa.String(), nullable=True),
        sa.Column("question", sa.String(), nullable=True),
        sa.Column("document_name", sa.String(), nullable=True),
        sa.Column("document_text", sa.String(), nullable=True),
        sa.Column("citation", sa.String(), nullable=True),
        sa.Column("authority_label", sa.String(), nullable=True),
        sa.Column("grounded", sa.Boolean(), nullable=True),
        sa.Column("answer", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_voice_gateway() -> None:
    op.create_table(
        "voice_gateway",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("call_sid", sa.String(), nullable=True),
        sa.Column("direction", sa.String(), nullable=True),
        sa.Column("to_number", sa.String(), nullable=True),
        sa.Column("from_number", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("voice", sa.String(), nullable=True),
        sa.Column("asr_engine", sa.String(), nullable=True),
        sa.Column("twilio_mode", sa.String(), nullable=True),
        sa.Column("call_status", sa.String(), nullable=True),
        sa.Column("twiml", sa.String(), nullable=True),
        sa.Column("recording_url", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_warm_transfer() -> None:
    op.create_table(
        "warm_transfer",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("call_sid", sa.String(), nullable=True),
        sa.Column("lead_name", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("broker_number", sa.String(), nullable=True),
        sa.Column("conference_name", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("whisper_text", sa.String(), nullable=True),
        sa.Column("transfer_status", sa.String(), nullable=True),
        sa.Column("whisper_delivered", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_qualification_and_broker_summary() -> None:
    op.create_table(
        "qualification_and_broker_summary",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("call_sid", sa.String(), nullable=True),
        sa.Column("lead_name", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("property_type", sa.String(), nullable=True),
        sa.Column("budget", sa.Float(), nullable=True),
        sa.Column("area", sa.String(), nullable=True),
        sa.Column("timeline", sa.String(), nullable=True),
        sa.Column("currency_setting", sa.String(), nullable=True),
        sa.Column("broker_summary", sa.String(), nullable=True),
        sa.Column("recommended_action", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_outcome_capture_and_ledger() -> None:
    op.create_table(
        "outcome_capture_and_ledger",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("call_sid", sa.String(), nullable=True),
        sa.Column("campaign", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=True),
        sa.Column("ledger_index", sa.Integer(), nullable=True),
        sa.Column("vector_clock", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_crm_destination_placeholder() -> None:
    op.create_table(
        "crm_destination_placeholder",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("crm_system", sa.String(), nullable=True),
        sa.Column("destination_url", sa.String(), nullable=True),
        sa.Column("payload_shape", sa.String(), nullable=True),
        sa.Column("delivery_state", sa.String(), nullable=True),
        sa.Column("mock_mode", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_notification() -> None:
    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("channel", sa.String(), nullable=True),
        sa.Column("recipient", sa.String(), nullable=True),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("trigger_event", sa.String(), nullable=True),
        sa.Column("delivery_state", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_local_drive() -> None:
    op.create_table(
        "local_drive",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("root_path", sa.String(), nullable=True),
        sa.Column("relative_path", sa.String(), nullable=True),
        sa.Column("operation", sa.String(), nullable=True),
        sa.Column("bytes_written", sa.Integer(), nullable=True),
        sa.Column("content_preview", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_google_drive() -> None:
    op.create_table(
        "google_drive",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("drive_mode", sa.String(), nullable=True),
        sa.Column("folder_id", sa.String(), nullable=True),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("operation", sa.String(), nullable=True),
        sa.Column("credential_setting", sa.String(), nullable=True),
        # Credential material the google_drive entity declares. alembic owns
        # the schema, so the columns the store round-trips are created here.
        sa.Column("GOOGLE_CLIENT_ID", sa.String(), nullable=True),
        sa.Column("GOOGLE_CLIENT_SECRET", sa.String(), nullable=True),
        sa.Column("GOOGLE_REFRESH_TOKEN", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def upgrade_mcp_adapter() -> None:
    op.create_table(
        "mcp_adapter",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("tool_name", sa.String(), nullable=True),
        sa.Column("catalog_scope", sa.String(), nullable=True),
        sa.Column("request_shape", sa.String(), nullable=True),
        sa.Column("response_shape", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )


def downgrade_lead_intake_and_dial_queue() -> None:
    op.drop_table("lead_intake_and_dial_queue")


def downgrade_call_state_machine() -> None:
    op.drop_table("call_state_machine")


def downgrade_project_knowledge_grounding() -> None:
    op.drop_table("project_knowledge_grounding")


def downgrade_voice_gateway() -> None:
    op.drop_table("voice_gateway")


def downgrade_warm_transfer() -> None:
    op.drop_table("warm_transfer")


def downgrade_qualification_and_broker_summary() -> None:
    op.drop_table("qualification_and_broker_summary")


def downgrade_outcome_capture_and_ledger() -> None:
    op.drop_table("outcome_capture_and_ledger")


def downgrade_crm_destination_placeholder() -> None:
    op.drop_table("crm_destination_placeholder")


def downgrade_notification() -> None:
    op.drop_table("notification")


def downgrade_local_drive() -> None:
    op.drop_table("local_drive")


def downgrade_google_drive() -> None:
    op.drop_table("google_drive")


def downgrade_mcp_adapter() -> None:
    op.drop_table("mcp_adapter")


def upgrade_work_queue() -> None:
    op.create_table(
        "work_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("capability_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True),
    )


def upgrade_idempotency() -> None:
    op.create_table(
        "idempotency",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("entity", sa.String(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
    )


def upgrade() -> None:
    upgrade_work_queue()
    upgrade_idempotency()
    upgrade_lead_intake_and_dial_queue()
    upgrade_call_state_machine()
    upgrade_project_knowledge_grounding()
    upgrade_voice_gateway()
    upgrade_warm_transfer()
    upgrade_qualification_and_broker_summary()
    upgrade_outcome_capture_and_ledger()
    upgrade_crm_destination_placeholder()
    upgrade_notification()
    upgrade_local_drive()
    upgrade_google_drive()
    upgrade_mcp_adapter()


def downgrade() -> None:
    op.drop_table("idempotency")
    op.drop_table("work_queue")
    downgrade_mcp_adapter()
    downgrade_google_drive()
    downgrade_local_drive()
    downgrade_notification()
    downgrade_crm_destination_placeholder()
    downgrade_outcome_capture_and_ledger()
    downgrade_qualification_and_broker_summary()
    downgrade_warm_transfer()
    downgrade_voice_gateway()
    downgrade_project_knowledge_grounding()
    downgrade_call_state_machine()
    downgrade_lead_intake_and_dial_queue()
