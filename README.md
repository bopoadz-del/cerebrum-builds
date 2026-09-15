# Automotive Platform

Cerebrum-builds session for **Automotive Platform** — operators manage vehicle inventory, customer leads, test-drive booking, and financing across branches.

Manufactured from vendored Store blocks (session `sess_4f5ad77f42a14781`):

- `automotive_core` — GENERATE kernel: listings, leads, test-drives, financing
- `dashboard` — REUSE `dashboard` (sales-lot board)
- `team` — REUSE `team` (sales / service / finance desks)
- `audit` — REUSE `audit` (listing / lead / testdrive trail)

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
