# Bakery Branch Operations Platform

Five branches, roughly 30 staff across owner/manager, counter, baking and
delivery roles, one set of books. Branch Outlook mailboxes take the orders;
this platform tracks the stock, the money, the dispatch and the follow-up,
and answers operational questions from the bakery's own uploaded documents.

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

`GET /health` is fail-closed: a missing disk, a closed database or a schema
behind head returns 503, not a green tick. `GET /` serves the console.

## Capabilities

| Capability | Entity | What it does |
|---|---|---|
| `branch_and_consolidated_operations` | `branch_and_consolidated_operations` | Per-branch views plus the owner/head-office rollup |
| `inventory_and_replenishment` | `inventory_and_replenishment` | Ingredients and finished goods, low-stock alerting, transfers |
| `branch_books_and_accounting` | `branch_books_and_accounting` | Sales, costs, price lists, margins, takings, expenses |
| `delivery_and_dispatch` | `delivery_and_dispatch` | Two cars, ten bikes, drivers, zones, routes, proof of delivery |
| `order_follow_up` | `order_follow_up` | Order status through baking, dispatch, delivery, follow-ups |
| `events_supply` | `events_supply` | Catering orders, quantities, deposits, delivery slots |
| `document_grounded_knowledge` | `document_grounded_knowledge` | Answers from the bakery's own documents, per tenant |
| `outlook_branch_messaging_integration` | `outlook_branch_messaging_integration` | Branch mailbox intake and status updates |

Each capability is a POST/GET surface:

```
POST /v1/<capability>          create one record (bearer token required)
GET  /v1/<capability>          list, filtered/sorted/paged on its own columns
GET  /v1/<capability>/{id}     read one record (404 across tenants)
```

Documents and questions:

```
POST /v1/rag/ingest            index a passage for the authenticated tenant
POST /v1/rag/query             retrieve + answer, with citations
GET  /v1/rag/query             same, question in the query string
GET  /v1/rag/documents         what this tenant has indexed
```

Tenancy is resolved from the bearer token (`app/tenancy.py`), never from the
request body. A cross-tenant read is a 404, never a 403: existence does not
leak.

## How a capability runs

1. The route authenticates, resolves the tenant, and validates the payload
   against the capability's own declared fields and constraints
   (missing required field or invalid enum → HTTP 422).
2. `app/kernel_bridge.py` runs `handle()` through the product kernel.
3. `handle()` invokes **every** block the capability binds, in-process, via
   `app.dispatch.execute(block_id, input, action=...)` — never a network call
   to a block store. Inputs the block needs (`steps`, `properties`,
   `checklist`, file paths, `sql`) are constructed from the record in
   `app/block_feed.py`, so a caller never has to know a block's vocabulary.
4. A block that answers with an error fails the capability closed: `ok:false`
   and nothing is persisted.
5. Only on success does the route write the request with the tenant-scoped
   `store.save`.

## Honest state of two vendored blocks

`app/vendor_compat.py` documents this, and the handlers repeat it in their
own responses as `unavailable_blocks`:

* `document_engine` — the CLONER vendored the wrapper as a package where its
  own loader expects a module file. The wrapper package imports cleanly and
  exposes the real `DocumentEngineBlock`, so it is registered under the name
  its loader looks for.
* `knowledge` — imports `vector_store` from `vendor.cerebrum.core`, which was
  not vendored. `app/retrieval.py` supplies those hooks, tenant-scoped, so the
  block searches this platform's own index.
* `notification` — its vendored source does not parse (a bare `try:` at line
  230 of `vendor/cerebrum/blocks/notification.py`). There is no block to run,
  so it is **not** shimmed: `app/notifications.py` records the outbound
  message in a local outbox and the handler names the block as unavailable
  rather than reporting a delivery that did not happen.

## Layout

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI app, lifespan migration, `/health`, `/` console |
| `app/routes.py` | capability POST/GET/GET-id routes + kernel job routes |
| `app/actions/` | one handler per capability (written by the factory WRITER role) |
| `app/dispatch.py` | local block dispatch (no network, no store callbacks) |
| `app/block_inputs.py`, `app/block_feed.py` | block input construction |
| `app/store.py` | SQLite persistence, `STORAGE_PATH/platform.db`, WAL, no DDL |
| `app/migrations.py`, `alembic/` | versioned schema (up and down) |
| `app/tenancy.py`, `app/auth.py`, `app/security.py` | tenant resolution, tokens, redaction |
| `app/authority.py` | precedence.v1 — which layer wins an answer, as data |
| `app/retrieval.py`, `app/llm.py`, `app/rag_routes.py` | the document surface |
| `app/formulas.py` | margins, takings, stock cover, deposits |
| `app/notifications.py` | offline outbox for branch messages |
| `scripts/acceptance.py` | 13 measured acceptance checks |
| `scripts/release_gate.py` | clone-and-test gate used by the Dockerfile |
| `frontend/src/` | operator console against the live routes |

## Known limits

* SQLite on one mounted disk is a single point of failure; backups live on the
  same volume. Documented in `docs/deploy.json`.
* The `notification` block cannot be loaded from this checkout's sealed vendor
  tree; delivery is the platform's own outbox until the vendored file is
  repaired upstream.
* No live Outlook connector is claimed. Branch mail is ingested through
  `outlook_branch_messaging_integration`, which indexes inbound mail and
  records outbound status updates; the Microsoft 365 transport is not wired.
