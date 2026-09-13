# Aviation Operations Hub

Cerebrum-builds session `sess_0caf3859ba9f44b6` for **Aviation Operations Hub** — fleet compliance, maintenance tracking, crew readiness, document control, and operational analytics. Manufactured from vendored Store blocks (`workflow`, `audit`, `file_hasher`, `database`, `validation`, `team`, `notification`, `document_engine`, `storage`, `dashboard`, `analytics`, `knowledge`, `vector_search`, `memory`).

Private Factory CLI-pivot scratch store. One branch per session. Store gate = GHA docker + `scripts/acceptance.py` (not Render).

## Roles

- operator
- admin

Mutating routes require `OPERATOR_TOKEN` / `ADMIN_TOKEN`. CORS uses `CORS_ALLOWLIST` only (`*` is refused).
