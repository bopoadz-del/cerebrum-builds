# Hotel Operations

A hotel operations platform for one or more properties: rooms and front-desk
operations, housekeeping and maintenance, guest engagement, and the operational
records behind them. It serves hotel staff and management (front desk,
housekeeping, maintenance, management) and answers staff questions from the
property's **own** uploaded documents — manuals, SOPs and rate sheets.

Offline by contract: no Store callbacks, no cloud LLM, no outbound HTTP except
the one connector the operator configures. Every block is vendored into this
repository and executed in-process.

## Run it

```sh
python -m pip install -r requirements.txt -r requirements-dev.txt

# local
export STORAGE_PATH=./data                 # the one persistence root
export PLATFORM_TOKEN=dev-local-token      # bearer token the API requires
uvicorn app.main:app --port 8000           # migrations run at boot
```

`GET /` serves the operator console (paste the token, then drive the
capabilities). `GET /health` is fail-closed: process, persistent disk, database
and Alembic head are each reported, and a failure answers 503. `GET /metrics`
serves request counts and latency.

```sh
python -m pytest tests                 # the whole suite
python -m pytest tests -m "not pilot"  # code-phase suite
python scripts/acceptance.py           # Store-green checklist (in-container)
```

## Settings — set these before you rely on them

**Money (no country, currency or tax regime was given, so none is assumed):**

| Setting | Required | Meaning |
| --- | --- | --- |
| `CURRENCY` | **yes, before any financial rule** | ISO code the property bills in. No default: the platform refuses to compute a folio total without it and names the setting. |
| `TAX_RATE_PERCENT` | **yes, before tax is computed** | The property's tax/VAT percentage. No default. |
| `CITY_TAX_PER_NIGHT` | optional (default 0) | Flat per-night accommodation/city tax, where the property has one. |

Every folio charge also carries a `setting` column: the name of the money
setting the charge was filed under (for example `currency`). It is required,
so a folio line always names the configuration whose money values it used;
`POST /v1/operations_billing` without it is refused with HTTP 422.

**Guest segmentation thresholds (yours to change; defaults are stated, not assumed):**
`RFM_CHAMPION_MONETARY` (1000), `RFM_LOYAL_MONETARY` (400),
`RFM_POTENTIAL_MONETARY` (100), `RFM_RECENT_DAYS` (60), `RFM_LAPSED_DAYS` (365).

**Tenancy:** `PLATFORM_TOKEN` (the platform token, default `dev-local-token`),
`TENANT_TOKENS` (`token:tenant,token:tenant`). A write always requires a token.
A **read** does too as soon as `TENANT_TOKENS` binds a second principal; in a
single-tenant deployment the console and the factory's own probes read the
platform's own tenant without a request-level principal. A record belonging to
another tenant is invisible: 404, never 403.

**Guest messaging (the one live outbound path):** `SMTP_HOST`, `SMTP_PORT`,
`SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_STARTTLS`, or `GUEST_WEBHOOK_URL`.
With neither configured, guest messaging refuses by name
(`delivery: not_configured`) instead of reporting a send that never happened.

**Deployment:** `STORAGE_PATH` (the one persistence root), `DATABASE_URL`
(Postgres when set; a SQLite file under `STORAGE_PATH` otherwise — `app/db.py`
is the only place that decides, and `app/store.py` takes its connection from
it), `SENTRY_DSN`, `PORT`.

`DATABASE_URL` accepts the scheme an operator would write (`postgres://` or
`postgresql://`) and `app/db.py` pins it onto `psycopg` (v3), the driver this
image installs — `requirements.txt` declares `psycopg[binary]`, so "Postgres
when set" is a connection the platform can dial rather than a scheme it
accepts and then fails on. `alembic/env.py` normalises through the same
function, so migrations and requests can never land on different databases.
The backup path follows the backend: `scripts/backup.sh` runs `pg_dump` when
`DATABASE_URL` is set and a SQLite `.backup` otherwise.

**How Store-green measures itself:** `scripts/acceptance.py` runs 21 checks.
Two of them — `docker_health_200` and `postgres_boot_200` — are measurements
only the gate host can take (it owns the container probe and the Postgres
server), and the script reports what the host measured and fails loud when the
host measured nothing. The rest it measures itself: it runs `scripts/bench.py`
for the p95, performs a real backup → wipe → restore drill with rows asserted
on both sides, and drives `app.notify.deliver` down a real SMTP socket to a
local sink. A host that exports `STORE_BENCH_P95_MS`, `STORE_BACKUP_RESTORE`,
`STORE_LIVE_CONNECTOR`, `STORE_POSTGRES_BOOT` or `STORE_DOCKER_HEALTH` wins —
but an unset variable means "this script measured it", not "nobody looked".

## What it does

| Capability | Blocks | What it does |
| --- | --- | --- |
| `property_and_room_registry` | `estate_registry`, `hotel_v2` | Registers buildings, floors, room types and rooms; the registry is the shared reference. |
| `front_desk_and_guest_stay` | `hotel_v2`, `workflow` | Reservations, arrivals, check-in/out and the stay card, through a prepared pipeline. |
| `housekeeping_and_maintenance` | `estate_maintenance`, `workflow` | Work orders for turnover and repair, their board, and dispatch to the ledger. |
| `guest_engagement_and_segmentation` | `guest_rfm_segmentation`, `channel_router`, `notification` | RFM segmentation, the routing decision, and guest messaging. |
| `document_and_knowledge_answers` | `document_engine`, `hotel_v2` | Parses an uploaded document into requirements/constraints/risks and classifies it. |
| `operations_billing` | `billing`, `hotel_v2` | Operational charges and folio totals, using only the operator's own currency and tax settings. |
| `operations_oversight_dashboard` | `dashboard`, `multi_tenant_rbac` | Occupancy, room status, open work orders and guest activity, authorised per operator role. |
| `external_integration_adapter` | `hospitality_connectors` | The single attach point for a property's PMS/POS/CMMS/loyalty systems; nothing is assumed. |

Retrieval: `POST /v1/rag/ingest` plants a document into the **calling tenant's**
corpus (its own Alembic tables, `rag_document` / `rag_chunk`),
`POST|GET /v1/rag/query` answers from it. Every answer carries its authority
layer (`precedence.v1`: certified > documents > formulas > procedures) and its
citations, and refuses by name when the corpus holds nothing that matches.

## Deploy

`Dockerfile` builds the image (no build step for the console: it is a
dependency-free page in `app/static/`), runs Alembic on boot, and answers its
healthcheck before traffic. `render.yaml` describes the Render service;
`scripts/entrypoint.sh` applies migrations then starts uvicorn.

`frontend/` is the same console as React components (`npm install && npm run
build` in an environment with Node, output to `app/static/`). The served
artifact does not need it.

## Known limits, stated

* `knowledge` (the vendored RAG block) cannot load in this delivery: it imports
  `vendor.cerebrum.core.vector_store`, which the runtime slice does not ship.
  Retrieval is therefore served by this platform's own tenant-scoped corpus
  (`app/retrieval.py`), not by that block. `external_integration_adapter` has the
  same shape for `mcp_adapter`, whose vendored adapter raises on
  `_LazyRegistry.items`. Both are named in `docs/blockers.json`; neither is
  silently skipped.
* Integrations beyond the vendored connector are not implemented, and no
  integration is assumed until the operator configures one.
