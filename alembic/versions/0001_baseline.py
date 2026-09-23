"""Baseline schema for CallOps: one table per capability.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-21

The entity's name IS its capability id - the stem of its handler module in
``app/actions/`` - so ``app/store.py`` can be called with
``store.save("<capability>", ...)`` and find a table. Every table carries
``tenant_id``: PSI's leads and a second brokerage's leads are rows in the
same schema, separated by tenancy, never by a second database.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "lead_intake_and_dial_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("lead_name", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("project_tag", sa.Text()),
        sa.Column("language", sa.Text()),
        sa.Column("campaign", sa.Text()),
        sa.Column("source_file", sa.Text()),
        sa.Column("lead_email", sa.Text()),
        sa.Column("property_type", sa.Text()),
        sa.Column("budget", sa.Float()),
        sa.Column("area", sa.Text()),
        sa.Column("timeline", sa.Text()),
        sa.Column("priority", sa.Integer()),
        sa.Column("phone_e164", sa.Text()),
        sa.Column("dialable", sa.Integer()),
        sa.Column("dialable_reason", sa.Text()),
        sa.Column("attempt_count", sa.Integer()),
        sa.Column("max_attempts", sa.Integer()),
        sa.Column("retry_backoff_minutes", sa.Integer()),
        sa.Column("daily_call_cap", sa.Integer()),
        sa.Column("concurrency", sa.Integer()),
        sa.Column("queue_state", sa.Text()),
        sa.Column("best_call_window", sa.Text()),
        sa.Column("window_state", sa.Text()),
        sa.Column("dial_scheduled_at", sa.Text()),
        sa.Column("next_attempt_at", sa.Text()),
        sa.Column("last_call_sid", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_lead_intake_and_dial_queue_tenant", "lead_intake_and_dial_queue", ["tenant_id"])

    op.create_table(
        "call_state_machine",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("call_sid", sa.Text()),
        sa.Column("lead_id", sa.Text()),
        sa.Column("lead_reference", sa.Text()),
        sa.Column("event", sa.Text()),
        sa.Column("previous_state", sa.Text()),
        sa.Column("current_state", sa.Text()),
        sa.Column("attempt_count", sa.Integer()),
        sa.Column("within_window", sa.Integer()),
        sa.Column("window_reason", sa.Text()),
        sa.Column("transition_allowed", sa.Integer()),
        sa.Column("refusal_reason", sa.Text()),
        sa.Column("guard_notes", sa.Text()),
        sa.Column("window_snapshot", sa.Text()),
        sa.Column("occurred_at", sa.Text()),
        sa.Column("source", sa.Text()),
        sa.Column("campaign", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_call_state_machine_tenant", "call_state_machine", ["tenant_id"])

    op.create_table(
        "project_knowledge_grounding",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("project_tag", sa.Text()),
        sa.Column("question", sa.Text()),
        sa.Column("claim_type", sa.Text()),
        sa.Column("language", sa.Text()),
        sa.Column("answer", sa.Text()),
        sa.Column("pitch", sa.Text()),
        sa.Column("citations", sa.Text()),
        sa.Column("source_documents", sa.Text()),
        sa.Column("retrieved_count", sa.Integer()),
        sa.Column("withheld", sa.Integer()),
        sa.Column("withheld_claims", sa.Text()),
        sa.Column("authority_layer", sa.Text()),
        sa.Column("authority_label", sa.Text()),
        sa.Column("divergence", sa.Text()),
        sa.Column("campaign", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_project_knowledge_grounding_tenant", "project_knowledge_grounding", ["tenant_id"])

    op.create_table(
        "voice_gateway",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("call_sid", sa.Text()),
        sa.Column("to_number", sa.Text()),
        sa.Column("voice_action", sa.Text()),
        sa.Column("from_number", sa.Text()),
        sa.Column("direction", sa.Text()),
        sa.Column("language", sa.Text()),
        sa.Column("call_status", sa.Text()),
        sa.Column("call_event", sa.Text()),
        sa.Column("transition_to", sa.Text()),
        sa.Column("mapping_ok", sa.Integer()),
        sa.Column("twiml", sa.Text()),
        sa.Column("asr_transcript", sa.Text()),
        sa.Column("tts_text", sa.Text()),
        sa.Column("tts_voice", sa.Text()),
        sa.Column("gather_language", sa.Text()),
        sa.Column("conference_sid", sa.Text()),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("attempt", sa.Integer()),
        sa.Column("provider", sa.Text()),
        sa.Column("call_key_source", sa.Text()),
        sa.Column("edge_stub", sa.Integer()),
        sa.Column("unavailable_blocks", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_voice_gateway_tenant", "voice_gateway", ["tenant_id"])

    op.create_table(
        "warm_transfer",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("call_sid", sa.Text()),
        sa.Column("outcome", sa.Text()),
        sa.Column("lead_id", sa.Text()),
        sa.Column("project_tag", sa.Text()),
        sa.Column("qualified_outcome", sa.Text()),
        sa.Column("broker_number", sa.Text()),
        sa.Column("broker_language", sa.Text()),
        sa.Column("whisper_text", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("steps", sa.Text()),
        sa.Column("step_count", sa.Integer()),
        sa.Column("conference_name", sa.Text()),
        sa.Column("conference_sid", sa.Text()),
        sa.Column("bridge_seconds", sa.Integer()),
        sa.Column("attempt", sa.Integer()),
        sa.Column("transfer_key", sa.Text()),
        sa.Column("edge_stub", sa.Integer()),
        sa.Column("unavailable_blocks", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_warm_transfer_tenant", "warm_transfer", ["tenant_id"])

    op.create_table(
        "qualification_and_broker_summary",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("call_sid", sa.Text()),
        sa.Column("outcome", sa.Text()),
        sa.Column("language", sa.Text()),
        sa.Column("project_tag", sa.Text()),
        sa.Column("lead_name", sa.Text()),
        sa.Column("property_type", sa.Text()),
        sa.Column("budget", sa.Float()),
        sa.Column("currency", sa.Text()),
        sa.Column("area", sa.Text()),
        sa.Column("timeline", sa.Text()),
        sa.Column("transcript", sa.Text()),
        sa.Column("collected", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("summary_text", sa.Text()),
        sa.Column("recommendation", sa.Text()),
        sa.Column("next_action", sa.Text()),
        sa.Column("qualified", sa.Integer()),
        sa.Column("transfer_required", sa.Integer()),
        sa.Column("authority_layer", sa.Text()),
        sa.Column("authority_label", sa.Text()),
        sa.Column("campaign", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_qualification_and_broker_summary_tenant", "qualification_and_broker_summary", ["tenant_id"])

    op.create_table(
        "outcome_capture_and_ledger",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("call_sid", sa.Text()),
        sa.Column("event_type", sa.Text()),
        sa.Column("sequence", sa.Integer()),
        sa.Column("prev_hash", sa.Text()),
        sa.Column("entry_hash", sa.Text()),
        sa.Column("payload_digest", sa.Text()),
        sa.Column("outcome", sa.Text()),
        sa.Column("actor", sa.Text()),
        sa.Column("campaign", sa.Text()),
        sa.Column("detail", sa.Text()),
        sa.Column("chain_ok", sa.Integer()),
        sa.Column("verified_count", sa.Integer()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_outcome_capture_and_ledger_tenant", "outcome_capture_and_ledger", ["tenant_id"])

    op.create_table(
        "crm_destination_placeholder",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("call_sid", sa.Text()),
        sa.Column("crm_system", sa.Text()),
        sa.Column("destination", sa.Text()),
        sa.Column("destination_named", sa.Integer()),
        sa.Column("payload_shape", sa.Text()),
        sa.Column("delivery", sa.Text()),
        sa.Column("unavailable_blocks", sa.Text()),
        sa.Column("outcome", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("note", sa.Text()),
        sa.Column("intended_method", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_crm_destination_placeholder_tenant", "crm_destination_placeholder", ["tenant_id"])

    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("trigger_event", sa.Text()),
        sa.Column("channel", sa.Text()),
        sa.Column("target", sa.Text()),
        sa.Column("subject", sa.Text()),
        sa.Column("body", sa.Text()),
        sa.Column("delivery", sa.Text()),
        sa.Column("provider", sa.Text()),
        sa.Column("attempts", sa.Integer()),
        sa.Column("response_code", sa.Integer()),
        sa.Column("delivered_at", sa.Text()),
        sa.Column("unavailable_blocks", sa.Text()),
        sa.Column("message_digest", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("outcome", sa.Text()),
        sa.Column("call_sid", sa.Text()),
        sa.Column("campaign", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_notification_tenant", "notification", ["tenant_id"])

    op.create_table(
        "local_drive",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text()),
        sa.Column("relative_path", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("content_digest", sa.Text()),
        sa.Column("bytes_written", sa.Integer()),
        sa.Column("root", sa.Text()),
        sa.Column("tenant_root", sa.Text()),
        sa.Column("entries", sa.Text()),
        sa.Column("file_exists", sa.Integer()),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("media_type", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_local_drive_tenant", "local_drive", ["tenant_id"])

    op.create_table(
        "google_drive",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text()),
        sa.Column("drive_mode", sa.Text()),
        sa.Column("folder_id", sa.Text()),
        sa.Column("document_id", sa.Text()),
        sa.Column("file_name", sa.Text()),
        sa.Column("mime_type", sa.Text()),
        sa.Column("credentials_present", sa.Integer()),
        sa.Column("unavailable_blocks", sa.Text()),
        sa.Column("delivery", sa.Text()),
        sa.Column("note", sa.Text()),
        sa.Column("would_call", sa.Text()),
        sa.Column("upload_state", sa.Text()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_google_drive_tenant", "google_drive", ["tenant_id"])

    op.create_table(
        "mcp_adapter",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("method", sa.Text()),
        sa.Column("tool", sa.Text()),
        sa.Column("arguments", sa.Text()),
        sa.Column("catalog_scope", sa.Text()),
        sa.Column("result", sa.Text()),
        sa.Column("tool_count", sa.Integer()),
        sa.Column("dispatched", sa.Integer()),
        sa.Column("error_code", sa.Text()),
        sa.Column("protocol", sa.Text()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("reference", sa.Text()),
        sa.Column("status", sa.Text()),
    )
    op.create_index("ix_mcp_adapter_tenant", "mcp_adapter", ["tenant_id"])



def downgrade() -> None:
    op.drop_index("ix_mcp_adapter_tenant", table_name="mcp_adapter")
    op.drop_table("mcp_adapter")
    op.drop_index("ix_google_drive_tenant", table_name="google_drive")
    op.drop_table("google_drive")
    op.drop_index("ix_local_drive_tenant", table_name="local_drive")
    op.drop_table("local_drive")
    op.drop_index("ix_notification_tenant", table_name="notification")
    op.drop_table("notification")
    op.drop_index("ix_crm_destination_placeholder_tenant", table_name="crm_destination_placeholder")
    op.drop_table("crm_destination_placeholder")
    op.drop_index("ix_outcome_capture_and_ledger_tenant", table_name="outcome_capture_and_ledger")
    op.drop_table("outcome_capture_and_ledger")
    op.drop_index("ix_qualification_and_broker_summary_tenant", table_name="qualification_and_broker_summary")
    op.drop_table("qualification_and_broker_summary")
    op.drop_index("ix_warm_transfer_tenant", table_name="warm_transfer")
    op.drop_table("warm_transfer")
    op.drop_index("ix_voice_gateway_tenant", table_name="voice_gateway")
    op.drop_table("voice_gateway")
    op.drop_index("ix_project_knowledge_grounding_tenant", table_name="project_knowledge_grounding")
    op.drop_table("project_knowledge_grounding")
    op.drop_index("ix_call_state_machine_tenant", table_name="call_state_machine")
    op.drop_table("call_state_machine")
    op.drop_index("ix_lead_intake_and_dial_queue_tenant", table_name="lead_intake_and_dial_queue")
    op.drop_table("lead_intake_and_dial_queue")
