# FinOps Central

A finance operations platform for roughly 40 department budget owners plus the
finance controllers and the CFO/approver roles. It unifies budget planning and
tracking, spend capture and categorisation, invoice/expense/budget-change
approvals, variance and variance-vs-budget analytics, cross-department
portfolio rollup, audit-ready evidence and validation, finance document
handling with knowledge lookup over invoices, contracts, policies and price
lists, a deterministic formula layer for the platform's own calculations, and
notification to owners and approvers.

Runs offline: vendored Store blocks are executed in-process, persistence is
SQLite on the mounted disk, and no call leaves the machine.

## Quick start

```sh
python -m pip install -r requirements.txt -r requirements-dev.txt
export STORAGE_PATH=./data            # where platform.db lives
python -m alembic upgrade head        # schema comes from Alembic, not connect()
uvicorn app.main:app --port 8000
# or: python -m pytest tests         (full suite, includes the pilot tests)
# or: python scripts/acceptance.py   (13 measured acceptance checks)
```

Open `/` for the console (it talks to the live routes), `/docs` for the
generated OpenAPI UI, `/health` for the fail-closed readiness report, and
`/v1/capabilities` for the capability surface.

## Capabilities

- `budget_planning_tracking` — Plan, allocate and track budgets by department, cost centre and budget owner, with versioned baselines and live utilisation against allocations.
- `spend_capture_categorisation` — Capture expenses, invoices and other spend events, categorise them against chart-of-accounts mappings, and link supporting documents.
- `approval_workflow` — Route expenses, invoices and budget change requests to the right approvers with thresholds, delegation, escalation and full status tracking.
- `variance_analytics` — Compute variance and variance-vs-budget analytics across departments, categories, periods and owners, with configurable formulas and rules of thumb.
- `dashboard_portfolio_rollup` — Provide department-level dashboards and a consolidated portfolio rollup for the CFO and controllers, showing spend, commitments, forecast and risks.
- `audit_evidence_validation` — Maintain an immutable audit trail and validate finance records, approvals and document integrity with hashed evidence and verifier checks.
- `finance_document_knowledge` — Store, parse and index uploaded invoices, contracts, policies and price lists, and answer finance questions through knowledge and vector search.
- `integrations_placeholders` — Provide marked-placeholder connectors for Google Drive invoice/document sync and Sage accounting, clearly labelled as not production-cleared, alongside the ready email/Slack notification path.

Every capability is one entity: `store.COLUMNS` is keyed by the capability id,
`alembic/versions/0001_baseline.py` creates one table per capability id with a
`tenant_id` column, and the route persists the request through the
tenant-scoped `store.save(entity, record, tenant_id)`. `handle()` is pure
dispatch; it never writes to the store.

## How a capability request is served

1. `POST /v1/<capability>` resolves the tenant from the bearer token
   (`app.tenancy`, never from the payload), validates the record against the
   model's own `FIELDS` + `CONSTRAINTS`, and rejects a reserved-keyword field.
2. `app.kernel_bridge.run_capability` runs `app.actions.<capability>.handle`
   through the vendored product kernel's `execute_action`, which fails the
   request if any block the handler called answered with an error.
3. `handle` constructs each bound block's own contract from the record
   (`app.block_feed` + `app.block_inputs`) and calls
   `app.dispatch.execute(block_id, input, action=…)` — the action travels as a
   keyword, never inside the payload.
4. Only on success does the route persist the request, and
   `GET /v1/<capability>` reads it back.

## Blocks

Handlers bind the Store blocks vendored under `vendor/blocks/`:
`analytics`, `audit`, `capture`, `dashboard`, `database`, `document_engine`,
`event_bus`, `evidence_verifier`, `file_hasher`, `formula_executor`,
`knowledge`, `notification`, `portfolio_rollup`, `queue`,
`recommendation_template`, `spec_analyzer`, `storage`, `team`, `validation`,
`vector_search`, `workflow`.

Two adaptations are worth naming:

- `app/vendor_compat.py` repairs a packaging mismatch (the `document_engine`
  wrapper package the CLONER vendored as a directory) and supplies the
  `vector_store` hooks the `knowledge` block imports, backed by this
  platform's own tenant-scoped index in `app/retrieval.py`.
- `vendor/cerebrum/blocks/notification.py` is sealed vendor source that does
  not parse (`IndentationError` at line 231). The handlers still invoke the
  `notification` block, record it in `unavailable_blocks` with the reason, and
  `app/notifications.py` performs the delivery into an offline outbox under
  `STORAGE_PATH`. That is a disclosed limitation, not a silent skip.

## Layout

| path | what it is |
|---|---|
| `app/models.py` | one dataclass per capability: `FIELDS`, `CONSTRAINTS`, `from_dict`/`to_dict` |
| `app/store.py` | SQLite over `STORAGE_PATH`; WAL + busy_timeout; tenant-scoped save/get/list/update/delete/query |
| `app/routes.py` | the HTTP surface for every capability, the kernel jobs and the work queue |
| `app/actions/<capability>.py` | one handler per capability (dispatch only) |
| `app/block_feed.py` | turns a finance record into each block's own input contract |
| `app/block_inputs.py` | shared block-input construction and the Store default-action map |
| `app/dispatch.py` | loads the vendored block and runs it in-process |
| `app/formulas.py` | utilisation, net/VAT split, variance, portfolio total/confidence/risk |
| `app/llm.py` | offline extractive answers plus the deterministic CFO recommendation brief |
| `app/retrieval.py`, `app/rag_routes.py` | tenant-scoped document index; `POST /v1/rag/ingest`, `POST|GET /v1/rag/query` |
| `app/tenancy.py`, `app/auth.py`, `app/security.py` | one tenant per request, resolved from the principal |
| `app/authority.py` | precedence.v1 — certified > documents > formulas > procedures |
| `app/health.py` | fail-closed readiness (process, disk, database, Alembic head) |
| `scripts/acceptance.py` | the measured acceptance suite (13 checks) |

## Integrations (honest placeholders)

- **Google Drive** — not cleared for factory builds and not attachable here.
  `integrations_placeholders` records the sync request and answers
  `not_implemented: Google Drive invoice/document sync is an owner-gated
  placeholder`. No file is fetched.
- **Sage** — same: `not_implemented: Sage accounting sync is an owner-gated
  placeholder`. No ledger entry is posted.
- **Email/Slack notification** — the ready path: `app/notifications.py` writes
  the outbound message to the local outbox and reports `network: false`.

## Tests

```sh
python -m pytest tests              # everything
python -m pytest tests -m "not pilot"   # code phase: imports, routes, handlers
python -m pytest tests -m pilot         # one-record round trip + execute-all
```

`tests/test_routes.py::test_every_capability_route_accepts_payload` POSTs a
payload built from each capability's own schema, then re-reads the record the
way a buyer does: create, list, get, and a 404 for an unknown id.
