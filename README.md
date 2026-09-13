# Retail Ops Tracker

Cerebrum-builds session for **Retail Ops Tracker** — a lightweight operations tracker for small retail teams. It centralizes inventory counts, order status, and a simple dashboard so staff can see what's in stock, what's been ordered, and what needs attention without adopting a full ERP.

Manufactured from vendored Store blocks:

- `inventory_tracking` — database, validation, audit
- `order_management` — workflow, queue, database, notification
- `ops_dashboard` — dashboard, analytics, database
- `stock_alerts` — notification, event_bus
- `pilot_ops_log` — knowledge, memory, storage

Offline platform. Channel `mcp` only. No HTTP store callbacks.

## Roles

- operator
- admin

Mutating routes require `OPERATOR_TOKEN` / `ADMIN_TOKEN`. CORS uses `CORS_ALLOWLIST` only (`*` is refused).

## Run

```
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Render-ready (`Dockerfile` + `render.yaml`) is packaging, not a live deploy. Store gate = GHA docker + `scripts/acceptance.py`.
