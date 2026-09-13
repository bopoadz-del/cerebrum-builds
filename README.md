# LedgerFlow

Cerebrum-builds session for **LedgerFlow** — personal finance for operators and admins. Manufactured from vendored Store blocks (`capture`, `storage`, `validation`, `dashboard`, `analytics`, `formula_executor`, `notification`, `workflow`, `document_engine`, `recommendation_template`, `audit`, `file_hasher`, `event_bus`, `queue`, `database`).

Private Factory CLI-pivot scratch store. One branch per session. Store gate = GHA docker + `scripts/acceptance.py` (not Render).

## Roles

- operator
- admin

Mutating routes require `OPERATOR_TOKEN` / `ADMIN_TOKEN`. CORS uses `CORS_ALLOWLIST` only (`*` is refused).
