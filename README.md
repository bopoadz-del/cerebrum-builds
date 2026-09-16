# RetailOS

RetailOS is a modern retail operations platform that unifies inventory,
sales, customers and analytics for small and mid-sized retail businesses
and multi-store operators. It gives operators real-time visibility into
stock levels, replenishment recommendations, customer insight and
performance dashboards in a single cloud-based system.

Written by the factory WRITER role (codewhale exec). Every capability
handler in `app/actions/` is agent-authored against the vendored Store
blocks in `vendor/blocks/`; nothing calls the block store over HTTP.

## Run it

```sh
pip install -r requirements.txt -r requirements-dev.txt
STORAGE_PATH=./data python -m alembic upgrade head
STORAGE_PATH=./data uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`GET /health` is fail-closed: it reports the process, the mounted disk, the
database and the Alembic head, and answers 503 when any of them is red.
Boot runs `upgrade_head()`; a revision behind head refuses to serve.

## Capabilities

| capability | entity | blocks | what it does |
| --- | --- | --- | --- |
| inventory_management | inventory_management | database, workflow, notification, validation | Track stock levels across locations, manage SKUs, automate reorder points |
| sales_and_orders | sales_and_orders | database, event_bus, workflow, queue | Process sales, orders, returns and exchanges across channels |
| customer_insights | customer_insights | database, analytics, vector_search, knowledge | Customer profiles, purchase history and segments |
| analytics_dashboard | analytics_dashboard | dashboard, analytics, portfolio_rollup, storage | Dashboards and reports on sales, turnover and store performance |
| supplier_and_purchasing | supplier_and_purchasing | database, workflow, recommendation_template, notification | Suppliers, purchase orders, lead times and reorder suggestions |
| omnichannel_integration | omnichannel_integration | event_bus, workflow, queue, knowledge | Store, e-commerce and marketplace sync |
| compliance_and_audit | compliance_and_audit | audit, validation, file_hasher, evidence_verifier | Audit trails, data privacy and secure transaction logging |

Every capability is one capability, one entity, one alembic table. A POST
writes the record through `app/store.py` and the handler runs its blocks
in-process: `POST /v1/{capability}` creates, `GET /v1/{capability}` lists,
`GET /v1/{capability}/{id}` reads one, `PUT` updates, `DELETE` deletes.
The blocks are action-dispatched: the handler passes `action=` as a
keyword (`BLOCK_DEFAULT_ACTIONS`), never inside the payload.

## Tenancy and authority

One tenant per request, always. The tenant comes from the authenticated
principal (`app/tenancy.py`), never from the payload: a body that names its
own tenant is refused. Roles (`operator`, `admin`) come from the same
principal and are checked in `app/security.py` before any block runs.

Answers carry their authority: `app/authority.py` implements precedence.v1
(layer 1 certified > 2 documents > 3 formulas > 4 procedures) as versioned
data, and `app/retrieval.py` indexes the platform corpus per tenant.

## Offline

The platform is offline by design (P1): the vendored block runtime is
imported in-process, `notification` publishes on the in-process `mcp`
channel, `vector_search` is the in-process index, and the knowledge
surface answers from this platform's own corpus. No Store URL, no cloud
LLM, no outbound HTTP at runtime. `tests/conftest.py` blocks outbound
sockets so a regression fails the suite instead of a customer's firewall.

## Tests

```sh
python -m pytest tests -m "not pilot"   # code-phase suite
python -m pytest tests -m pilot         # Store-backed round trips
python3 scripts/release_gate.py         # the deploy gate
python3 scripts/acceptance.py           # the 12 measured Store checks
```

## Deploy

`Dockerfile` pins `python:3.12-slim` by digest, installs
`requirements.txt`, runs `scripts/release_gate.py` at build time (a red
suite must not produce a deployable image), and serves
`uvicorn app.main:app` through `scripts/entrypoint.sh`, which applies
`alembic upgrade head` against the mounted disk first. `render.yaml`
declares the single web service and the 1 GB disk at `/app/data`.
Render-ready is not a live deploy: nobody has deployed this checkout.

## Known limitations

- No live Render deployment and no Store-built Docker acceptance run in
  this checkout; both are owner-gated.
- `evidence_verifier` and `portfolio_rollup` are vendored echo blocks: the
  platform feeds them real records and persists their answer, but the
  verification/roll-up logic itself lives upstream, not here.
- The marketplace and e-commerce connectors are not built: omnichannel
  records what was synced and publishes it on the bus; it does not talk to
  a marketplace API (the platform is offline by contract).
