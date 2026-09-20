# Construction Platform

Day-to-day running of live civil-works jobs for a small UAE contractor, plus
commercial control and document-backed answers. One to five concurrent jobs,
three to ten people: owner (sees everything, approves), site engineer/foreman
(daily site records, progress, snags), accounts (valuations, payment
applications, invoices, supplier/subcontractor payments).

Amounts are in **AED**. Country (United Arab Emirates) and currency (AED) come
from the brief. **No tax rate comes from the brief**, so none is assumed — see
*Money settings* below.

## Run it

```sh
pip install -r requirements.txt -r requirements-dev.txt
export STORAGE_PATH=./data            # sqlite file + block stores live here
export UAE_VAT_RATE_PERCENT=5         # required: see Money settings
export DEFAULT_RETENTION_PERCENT=10   # required
export PAYMENT_TERM_DAYS=30           # required
python -m pytest -m "not pilot" -q    # code phase
python -m pytest -m pilot -q          # post-boot: one-record round trip per capability
sh scripts/entrypoint.sh              # alembic upgrade head && uvicorn app.main:app
```

Open `http://127.0.0.1:8000/` for the operator console. `GET /health` is
fail-closed (process, disk, database, alembic head). `GET /v1/jobs`,
`/v1/catalog`, `/v1/inventory`, `/v1/capabilities`, `/v1/gates`,
`/v1/provenance` publish each build kernel's job description.

## Capabilities

Each capability is one table (its own name), one module in `app/actions/`, and
one HTTP surface: `POST /v1/<capability>` (create), `GET /v1/<capability>`
(list, filter/sort/page over its own columns), `GET|PUT|DELETE
/v1/<capability>/{id}`.

| Capability | What it does | Store blocks |
| --- | --- | --- |
| `job_and_site_tracking` | Active jobs, sites, work fronts, milestones, progress %, snag counts, variations with approval status | workflow, database, estate_registry, validation |
| `commercials_and_valuations` | BOQ lines, measured quantities, interim payment applications/valuations, retention, variation orders, invoices, supplier/subcontractor POs and payment tracking | formula_executor, document_engine, database, validation |
| `document_qa_and_indexing` | Index BOQs, drawings, method statements, safety procedures, price lists; ask questions with source references | capture, storage, vector_search, knowledge, file_hasher |
| `safety_and_compliance` | Method statements and safety procedures per job, incident/near-miss log, readiness check before a work front opens | estate_maintenance, readiness_engine, workflow, validation |
| `progress_cost_dashboard` | Cross-job roll-up: progress, certified value, cost to date, variations pending, snags open, payments due | portfolio_rollup, dashboard, analytics |
| `automation_reminders_escalation` | Monthly valuation reminder and escalation when variations or snags pass a threshold | queue, event_bus, notification, workflow, recommendation_template |
| `audit_and_access_control` | Audit trail of approvals, document versions and financial changes; role-based access | audit, team, validation, database |
| `team_notifications` | Email/messaging-channel notifications on approvals, due valuations, overdue items | notification, event_bus |

Handlers are pure dispatch: the route's tenant-scoped `store.save(payload)`
persists the request after the kernel reports success. A block refusal is
reported as `ok: false` with the block named — never as a green response.

## Money settings (set these before use)

Country and currency are fixed by the brief (United Arab Emirates, AED). Every
**rate** is a named setting read from the environment with **no default**; an
unset rate is refused by name rather than guessed. `GET /v1/settings/money`
reports which are set.

| Setting | Meaning |
| --- | --- |
| `UAE_VAT_RATE_PERCENT` | UAE VAT rate applied to a valuation, in percent. The contractor's registration position decides the value (standard-rated, zero-rated, reverse charge). |
| `DEFAULT_RETENTION_PERCENT` | Retention withheld from a valuation where the contract does not name one, in percent. |
| `PAYMENT_TERM_DAYS` | Days between a certified valuation and its payment due date. |

A valuation is priced by `POST /v1/formulas/valuation`:
`certified = gross − retention + VAT`, where a rate carried on the record wins
over the deployment setting, and the answer says which source it used. A
setting that is missing is answered as `{"ok": false, "setting": "<NAME>"}`.

Also set `PLATFORM_TOKEN` (bearer token for the platform tenant) and
`STORAGE_PATH`. Optional: `TENANT_TOKENS` (`token:tenant,token:tenant`) and
`TENANT_NAMES` for additional tenants.

## Document Q&A / retrieval

`app/rag_routes.py` serves an **offline lexical index** inside the platform's
sqlite file: `POST /v1/rag/ingest`, `GET|POST /v1/rag/query` (twins under
`/v1/steward/rag/*`). It is keyword retrieval with inverse-document-frequency
weighting, not an embedding model — say so to the customer, because it is what
runs. Every read is scoped by the tenant resolved from the bearer token, never
from the payload. `GET /v1/retrieval?q=` ranks the tenant's own capability rows
the same way, and `POST /v1/authority/resolve` ranks claims under
`precedence.v1` (certified → documents → formulas → procedures) and returns the
winner plus every divergence.

## Authority

Anything the console shows carries its layer label: certified record, uploaded
document, platform formula, or standing procedure. The model never chooses the
winner; `app/authority.py` ranks the claims and records the divergences.

## What is not built (named, not faked)

* **No model provider.** `app/llm.py` is a deterministic template composer and
  `is_available()` returns `False`; anything needing real inference is refused.
* **No network.** Runtime is offline: no outbound HTTP, no cloud LLM, no
  document store callbacks. `NOTIFICATION_CHANNEL=mcp` delivers in-process.
* **External systems.** No accounting/ERP package, cloud drive or messaging
  connector was named by the team. When one is named it ships as a marked
  placeholder until built; nothing here pretends to talk to one.
* **Email/webhook delivery** requires credentials the operator supplies
  (`SMTP_*` / `WEBHOOK_URL`); without them the notification block records the
  delivery in-process and reports `channel: "mcp"`.

## Layout

```
app/main.py            FastAPI app factory, /health, UI
app/models.py          MODELS: capability -> dataclass (FIELDS, CONSTRAINTS, from_dict/to_dict)
app/actions/*.py       one handler per capability (CAPABILITY_ID, handle(payload))
app/routes.py          capability HTTP surface (tenant-scoped persist)
app/routers/operator.py retrieval, money settings, valuation formulas, authority
app/rag_routes.py      document ingest/query (offline lexical index)
app/store.py           sqlite persistence (WAL, busy_timeout); schema belongs to alembic
alembic/versions/     0001_baseline (one table per capability), 0002 lifecycle audit, 0003 extras
app/formulas.py        BOQ line value, retention, VAT, certified value, payment due
app/money.py           country/currency constants and the no-default rate settings
app/authority.py       precedence.v1 ranking
app/dispatch.py        local block dispatch over the vendored Store blocks
app/block_inputs.py    builds each block's accepted input from the domain record
tests/                 code-phase suite (not pilot) and post-boot pilot suite
scripts/acceptance.py  Store-green acceptance, 13 measured checks
scripts/release_gate.py code-phase release gate (run inside the image build)
frontend/              Vite/React source for the same console; the image serves app/static/index.html
vendor/blocks/         sealed Store blocks, vendored by CLONER (read-only)
```

Code phase: `python -m pytest -m "not pilot" -q`. Pilot (needs the booted
product and the vendored stock): `python -m pytest -m pilot -q`.
