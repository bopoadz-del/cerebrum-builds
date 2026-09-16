# LexManage

LexManage is a practice management platform for law firms: matters, client
intake, document handling, time and billing, a client portal, operational
analytics and compliance audit — one runnable service, no external
dependencies.

Built by the CerebrumDev factory WRITER role. Every capability handler in
`app/actions/` was authored for this product; the platform plumbing
(dispatch, routes, migrations, acceptance) is the factory's own emitter
output, re-generated for this blueprint.

## What this is

A standalone platform. Every capability runs in-process: handlers invoke the
blocks vendored into `vendor/blocks/` at build time through `app/dispatch.py`.
There is **no call back to a block store at runtime** — the platform runs with
the factory switched off.

## Capabilities

| Capability | Entity | Registry-verified blocks |
|---|---|---|
| `matter_management` | `matter_management` | `workflow`, `database`, `document_engine`, `notification` |
| `client_intake` | `client_intake` | `workflow`, `formula_executor`, `validation`, `document_engine` |
| `document_management` | `document_management` | `storage`, `document_engine`, `vector_search`, `audit` |
| `time_and_billing` | `time_and_billing` | `formula_executor`, `database`, `notification`, `analytics` |
| `client_portal` | `client_portal` | `dashboard`, `document_engine`, `notification`, `storage` |
| `legal_analytics` | `legal_analytics` | `analytics`, `dashboard`, `portfolio_rollup`, `knowledge` |
| `compliance_audit` | `compliance_audit` | `audit`, `validation`, `readiness_engine`, `evidence_verifier` |

## Vendored blocks

`analytics`, `audit`, `dashboard`, `database`, `document_engine`,
`evidence_verifier`, `formula_executor`, `knowledge`, `notification`,
`portfolio_rollup`, `readiness_engine`, `storage`, `validation`,
`vector_search`, `workflow` — pinned in `blocks.lock.json` and verified
against their published digests by the CLONER gate.

## HTTP surface

```
GET    /health                          fail-closed process/disk/db/head check
GET    /                                the operator console (app/static/index.html)
POST   /v1/{capability}                 create (bearer token required)
GET    /v1/{capability}                 list, filter/sort/page
GET    /v1/{capability}/{id}            fetch one
PUT    /v1/{capability}/{id}            update
DELETE /v1/{capability}/{id}            delete
GET    /v1/schema/{capability}          the capability's own contract
GET    /v1/jobs                         the five kernel job descriptions
GET    /v1/capabilities                 capability roster
GET    /v1/gates                        tester coverage (does not run tests)
GET    /v1/provenance                   block provenance and substitutions
GET    /v1/roles  /v1/formulas  /v1/authority  /v1/llm  /v1/offline
POST   /v1/rag/ingest                   ingest a firm document
GET    /v1/rag/query?q=...              tenant-scoped retrieval, cited
POST   /v1/rag/query
```

Writes require `Authorization: Bearer $PLATFORM_TOKEN`
(`POST /v1/<capability>` without it is 401; a missing required field or an
out-of-vocabulary enum is 422).

## Status vocabulary

`status` is schema-enforced, not prose: `open`, `in_progress`, `closed`.
Routes, models (`app/models.py`), and the Alembic tables all carry the same
vocabulary and the routes reject anything outside it.

## Tenancy and authority

One tenant per request, always. Corpus access goes through the tenant store
resolved from the authenticated principal (`app/tenancy.py`), never a
client-supplied name. Answers are assembled from a versioned precedence
ladder (`app/authority.py`, precedence.v1): 1 certified protocols > 2 firm
documents > 3 formulas > 4 procedures. The model is told the winner; every
answer carries divergence records and per-claim labels.

## Running it

```sh
pip install -r requirements.txt
STORAGE_PATH=/var/lib/lexmanage PLATFORM_TOKEN=change-me \
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Boot applies `alembic upgrade head` (the lifespan refuses to start when a
revision is behind head), then the platform preconditions.

## Tests

```sh
pytest -m "not pilot"     # code-phase: imports, handlers, routes, models
pytest -m pilot           # booted product: per-capability round-trip, RAG
python scripts/release_gate.py
python scripts/acceptance.py   # the 12 measured Store checks
```

## Offline posture

No outbound HTTP at runtime, ever. The vendored Store runtime is used as
shipped; three sealed modules in this pin cannot be imported at all, and each
has a real in-process substitute rather than a stub —
see `docs/known_limitations.json` and `GET /v1/provenance`. `notification`
spools locally and reports `delivered: false`; `knowledge` answers
extractively from the firm's own corpus and says `grounded: false` when there
is no match; `document_engine` extracts from what it was actually given.

## Layout

```
app/main.py            FastAPI app factory, fail-closed /health
app/models.py          MODELS: capability -> dataclass with FIELDS/CONSTRAINTS
app/actions/*.py       one handler per capability (CAPABILITY_ID, handle)
app/routes.py          the capability HTTP surface
app/routers/           schema, roles, formulas, authority, llm, offline
app/rag_routes.py      tenant-scoped ingest/query
app/dispatch.py        in-process block dispatch (action= keyword)
app/block_inputs.py    per-block input construction
app/store.py           sqlite persistence (schema owned by Alembic)
app/formulas.py        the firm's formula catalogue
app/retrieval.py       the firm's tenant-scoped lexical corpus
alembic/versions/      versioned schema
frontend/src/          operator console modules
scripts/               release gate, acceptance, entrypoint, rollback
```
