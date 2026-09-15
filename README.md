# Productivity Platform

Cerebrum-builds session for **Productivity Platform** — a tiny single-page notes app: save a note with a title and body, list notes, search notes by keyword, delete a note. Nothing else.

Manufactured from vendored Store blocks:

- `productivity_core` — GENERATE notes kernel (no block ids)
- `audit` — REUSE Store `audit` via `execute(action=)`

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
