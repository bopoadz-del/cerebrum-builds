# Veterinary Care Platform

Cerebrum-builds session for **Veterinary Care Platform** (VetCare Hub) — a clinic-operations hub for veterinary practice operators. It centralizes patient charts, appointment slots, prescriptions, invoices, and client messages so a small clinic can run a pilot without a full PIMS.

Manufactured from vendored Store blocks (session `sess_69f28c0d8bc540e9`):

- `veterinary_care_core` — analytics
- `patient_records_management` — knowledge, vector_search, memory
- `appointment_scheduling` — workflow, event_bus, notification, queue
- `prescription_management` — validation, analytics
- `billing_and_invoicing` — validation, notification, queue
- `client_communication_portal` — notification, event_bus, knowledge
- `audit` — audit (persistable capability)
- `dashboard` — dashboard, analytics (persistable capability)

Offline platform. Channel `mcp` only. No HTTP store callbacks.

## Roles

- operator
- admin

Mutating routes require `OPERATOR_TOKEN` / `ADMIN_TOKEN`. CORS uses `CORS_ALLOWLIST` only (`*` is refused). Client `actor` / `user_id` is `claimed_actor` only.

## Run

```
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Render-ready (`Dockerfile` + `render.yaml`) is packaging, not a live deploy. Store gate = GHA docker + `scripts/acceptance.py`.
