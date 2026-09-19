# Bakery Chain Operations & Delivery Platform

Written by the factory WRITER role (codewhale exec)

A management platform for a bakery chain: five retail bakeries, an in-house
delivery fleet (10 drivers, 10 bikes, 2 cars, ~30 deliveries/day), and central
management. It runs offline and in-process — no network, no block store, no
outbound call at runtime. Every block executes from the source vendored into
`vendor/blocks/` at build time and pinned by `blocks.lock.json`.

## What it does

| Capability | What it holds |
| --- | --- |
| `stock_inventory_management` | per-shop ingredient/product/supply stock, reorder thresholds, waste and transfers between the five bakeries |
| `product_pricing` | product catalogue with unit costs, margins, price-list versions and the derived selling price per product and shop |
| `delivery_dispatch_tracking` | orders, driver and vehicle assignment (bike/car), delivery state from pickup to drop-off across ~30 daily deliveries |
| `fleet_cost_tracking` | fuel or charge, maintenance, insurance and per-delivery cost for the ten bikes and two cars |
| `management_reporting_dashboard` | chain-wide sales, stock, delivery and fleet KPIs with drill-downs |
| `user_roles_workforce` | manager and driver accounts, roles, shop assignment and shift planning |
| `document_knowledge_qa` | recipes, cost sheets, price lists and delivery procedures indexed for grounded answers over the tenant corpus |
| `procedures_readiness_and_audit_trail` | per-shop and per-run checklists, readiness before service, and the immutable evidence trail of checks |


## Run it

```sh
pip install -r requirements.txt
STORAGE_PATH=./data uvicorn app.main:app --port 8000
# -> http://127.0.0.1:8000/        operator console
# -> http://127.0.0.1:8000/health  fail-closed readiness (200 or 503)
# -> http://127.0.0.1:8000/docs    OpenAPI
```

The schema is Alembic-versioned and applied on boot (`alembic/versions/`).
`app/store.py` never creates a table: a missing revision is a fail-closed 503,
not a silently empty product.

## HTTP surface

* `POST /v1/{capability}` — token-guarded create. The body is validated against
  the capability's own schema (422 on a missing required field, an
  out-of-vocabulary `status`, a broken bound, or a reserved keyword), handed to
  the handler, and persisted **only** when the handler reports success.
* `GET /v1/{capability}` — list; `GET /v1/{capability}/{id}` — one record.
* `POST /v1/rag/ingest`, `GET|POST /v1/rag/query` — the knowledge-layer corpus
  under `STORAGE_PATH` (unit prices and procedures once uploaded).
* `GET /v1/jobs`, `/v1/catalog`, `/v1/capabilities`, `/v1/inventory`,
  `/v1/gates`, `/v1/provenance` — the kernel job descriptions.

Envelope vocabulary is schema-enforced, not prose: `status` is exactly
`open | in_progress | closed`, and a route rejects anything else with HTTP 422
before a handler is called. Every table carries a `tenant_id`; the tenant comes
from the authenticated principal, never from the body or a header override.

## Tenancy and authority

One tenant per request. Reads and writes are scoped by the principal's tenant;
an `X-Tenant` header that disagrees with the principal is refused with 403.
`app/authority.py` holds the precedence ladder (certified > documents >
formulas > procedures), versioned as data, and `app/llm.py` is a local,
offline answer surface — nothing reaches a provider.

## Tests

```sh
python -m pytest -m "not pilot"   # code phase: imports, dispatch, models, routes
python -m pytest -m pilot         # one-record round-trip per capability
python scripts/acceptance.py      # 14 measured checks (Store image harness)
python scripts/release_gate.py    # fail-closed packaging gate
```

`tests/conftest.py` forces an isolated `STORAGE_PATH` and refuses outbound
connections, so a suite run can never touch a real data file or the network.

## Deploy

`Dockerfile` builds the offline image (it runs `scripts/release_gate.py` at build
time and refuses to build an incomplete tree); `render.yaml` describes the
render-ready service with a persistent disk mounted at `/data`. That is
render-ready, not a live deploy.
