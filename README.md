# AirOps Portfolio

Cerebrum-builds session for **AirOps Portfolio** — Riyadh Air (RX) enterprise technology portfolio. Manufactured from vendored Store blocks (`audit`, `dashboard`) plus GENERATE handlers for aviation kernel, portfolio, hybrid delivery, milestones, KPI, budget, demand, ERP workstream, GDPR, governance, and ops context.

Private Factory CLI-pivot scratch store. One branch per session. Store gate = GHA docker + `scripts/acceptance.py` (not Render).

## Roles

- operator
- admin

Mutating routes require `OPERATOR_TOKEN` / `ADMIN_TOKEN`. CORS uses `CORS_ALLOWLIST` only (`*` is refused).
