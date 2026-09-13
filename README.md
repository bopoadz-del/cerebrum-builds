# Airport Operations Platform

Cerebrum-builds session for **Airport Operations Platform** — an integrated operations platform for airport authorities and airside teams. It unifies flight, resource, and readiness data into a single command view: aircraft turnarounds, gate and stand allocation, ground crew dispatch, work orders, regulatory documents, and incident evidence.

Manufactured from vendored Store blocks:

- `airport_readiness` — analytics
- `operational_dashboard` — dashboard, analytics, notification
- `ground_workflow_coordination` — workflow, team, queue
- `regulatory_document_control` — document_engine, validation, audit, storage
- `incident_evidence_tracking` — capture, file_hasher, storage
- `flight_event_orchestration` — event_bus, workflow, notification, queue
- `airport_knowledge_assistant` — knowledge, vector_search, recommendation_template, memory

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
