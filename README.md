# AirOps Portfolio — Aviation Operations Hub

Cerebrum-builds session for **Aviation Operations Hub** on **AirOps Portfolio** — Riyadh Air (RX). Fleet compliance, aircraft maintenance, crew readiness, flight document control, operational analytics, and safety knowledge, plus the enterprise technology portfolio. Manufactured from vendored Store blocks (`workflow`, `audit`, `file_hasher`, `database`, `validation`, `team`, `notification`, `document_engine`, `storage`, `dashboard`, `analytics`, `knowledge`, `vector_search`, `memory`).

Private Factory CLI-pivot scratch store. One branch per session. Store gate = GHA docker + `scripts/acceptance.py` (not Render).

## Roles

- operator
- admin

Mutating routes require `OPERATOR_TOKEN` / `ADMIN_TOKEN`. CORS uses `CORS_ALLOWLIST` only (`*` is refused).
