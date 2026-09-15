# Automotive Platform

Cerebrum-builds session for **Automotive Platform** — a car dealership workspace for vehicle inventory (make, model, year, price, mileage, VIN, new/used), leads, test-drive booking, financing interest, and a sales-team dashboard. Multi-branch inventory.

Manufactured from vendored Store blocks:

- `automotive_core` — GENERATE vehicle inventory kernel (no block ids)
- `dashboard` — REUSE `dashboard`
- `team` — REUSE `team`
- `audit` — REUSE `audit`

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
