"""HAT manifests for CallOps.

Written by the factory WRITER role (codewhale exec)

One base agent and one hat per capability: a hat is the narrow scope a
capability may act inside, and the base agent holds only the union of the
hats it is allowed to wear.
"""

HAT_INDEX = [
  {
    "agent_id": "callops.base",
    "file": "callops_base.json",
    "kind": "base"
  },
  {
    "agent_id": "callops.hat.lead_intake_and_dial_queue",
    "file": "callops_hat_lead_intake_and_dial_queue.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.call_state_machine",
    "file": "callops_hat_call_state_machine.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.project_knowledge_grounding",
    "file": "callops_hat_project_knowledge_grounding.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.voice_gateway",
    "file": "callops_hat_voice_gateway.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.warm_transfer",
    "file": "callops_hat_warm_transfer.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.qualification_and_broker_summary",
    "file": "callops_hat_qualification_and_broker_summary.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.outcome_capture_and_ledger",
    "file": "callops_hat_outcome_capture_and_ledger.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.crm_destination_placeholder",
    "file": "callops_hat_crm_destination_placeholder.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.notification",
    "file": "callops_hat_notification.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.local_drive",
    "file": "callops_hat_local_drive.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.google_drive",
    "file": "callops_hat_google_drive.json",
    "kind": "hat"
  },
  {
    "agent_id": "callops.hat.mcp_adapter",
    "file": "callops_hat_mcp_adapter.json",
    "kind": "hat"
  }
]
