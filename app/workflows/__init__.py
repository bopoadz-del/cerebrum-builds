WORKFLOWS = [
  {
    "description": "Default linear workflow over planned capabilities.",
    "name": "Capability sequence",
    "steps": [
      {
        "capability_id": "matter_management",
        "role": "execute"
      },
      {
        "capability_id": "client_intake",
        "role": "execute"
      },
      {
        "capability_id": "document_management",
        "role": "execute"
      },
      {
        "capability_id": "time_and_billing",
        "role": "execute"
      },
      {
        "capability_id": "client_portal",
        "role": "execute"
      },
      {
        "capability_id": "legal_analytics",
        "role": "execute"
      },
      {
        "capability_id": "compliance_audit",
        "role": "execute"
      }
    ],
    "workflow_id": "legal_practice_management.capability_sequence"
  }
]
