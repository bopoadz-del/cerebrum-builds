# Boutique Front Desk

A lightweight front-desk platform for a 40-room boutique hotel. Staff record a
guest check-in (guest name, room number, nights, arrival time); the duty
manager sees the day's arrivals. It replaces paper logs and ad-hoc
spreadsheets with one shared, reliable arrival board for a small hotel team.

Runs offline: no network, no block store callbacks, no cloud LLM. Blocks are
vendored into this checkout and dispatched in process (`app/dispatch.py`).

## Capabilities

| capability | what it does | blocks |
| --- | --- | --- |
| `record_checkin` | records one guest check-in | capture, validation, database |
| `todays_arrivals_board` | today's check-ins, arrived or expected | dashboard, database, analytics |
| `room_availability_check` | is the room free for the dates (double-booking guard) | validation, database, formula_executor |
| `guest_notes_and_preferences` | short notes for the front desk | database, memory |
| `checkin_notifications` | tell housekeeping and the duty manager | event_bus, queue |
| `daily_checkin_summary` | end-of-day arrivals / occupancy / no-shows | analytics, database, dashboard |
| `audit_trail` | who recorded or changed each check-in | audit, database |

## Run

```sh
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests                 # full suite
python -m pytest -m "not pilot"        # code-phase suite
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`STORAGE_PATH` relocates the SQLite file (default `./data/platform.db`). Schema
is versioned Alembic (`app/migrations.py` + `alembic/versions/`); `connect()`
never creates tables, and boot refuses when a revision is behind head.

## HTTP surface

* `POST /v1/<capability>` — record one, requires `Authorization: Bearer <token>`
* `GET /v1/<capability>` — this tenant's records (filter/sort/page by column);
  a token is honoured when presented, and a board read that presents none
  serves the platform's own front-desk tenant (see Tenancy below)
* `GET|PUT|DELETE /v1/<capability>/{id}` — one record; cross-tenant reads 404
* `GET /v1/jobs`, `/v1/catalog`, `/v1/inventory`, `/v1/capabilities`,
  `/v1/gates`, `/v1/provenance` — the five kernel job descriptions
* `GET /v1/vendor_health` — live loadability of every bound block
* `POST|GET /v1/corpus/documents`, `GET /v1/answers` — tenant corpus and
  grounded, precedence-labelled answers
* `POST /v1/rag/ingest`, `POST|GET /v1/rag/query`, `GET /v1/rag/documents` —
  the same tenant corpus under the RAG names the platform's acceptance probe
  looks for (steward twins at `/v1/steward/rag/*`); ingest writes one
  `corpus_documents` row for the token's tenant, query ranks only that
  tenant's rows and returns excerpts plus scores, and a term that was never
  planted comes back empty
* `GET /v1/precedence`, `/v1/formulas`, `/v1/llm` — authority layers, the
  versioned formula registry, and what the answer adapter really is
* `GET /health` — fail-closed (process, disk, database, migrations)

The browser UI is served at `/` from `app/static/index.html`, built on
`frontend/src/api.ts` (the same live routes — no second API).

## Tenancy and authority

One tenant per request, always. Every store call is tenant-scoped and the
tenant is never taken from the body, a query string, or an `X-Tenant`
header — a header that disagrees with the resolved tenant is refused with
403.

Writes (`POST` / `PUT` / `DELETE`) require `Authorization: Bearer <token>`
and write under the tenant that token resolves to. Reads resolve a presented
token the same way (an unknown or unbound token is 401 — a bad credential
never degrades into an anonymous read). A read that presents no credential
at all serves the platform's own front-desk tenant (`local`), because the
arrival board is polled by the duty-manager display, which holds no per-user
token.

Authority is versioned data (`precedence.v1`, `app/authority.py`): 1 certified
> 2 documents > 3 formulas > 4 procedures. The answer path is *told* the
winner and never chooses one; every answer carries per-claim labels and the
divergence records (`app/llm.py`).

## Known blockers (named, never stubbed)

Two vendored slices in this checkout cannot load, so no capability binds them.
Both are recorded in `docs/blockers.json` and probed live on
`GET /v1/vendor_health`:

* `notification` — `vendor/cerebrum/blocks/notification.py` does not parse
  (`IndentationError`, line 231). `checkin_notifications` delivers over the
  `event_bus` publish path plus a durable `queue` job instead.
* `knowledge` — `vendor/cerebrum/blocks/knowledge.py` imports
  `vendor.cerebrum.core.vector_store`, which the vendored core slice does not
  ship. `guest_notes_and_preferences` stores through `database` and caches in
  `memory`; the tenant corpus (`app/retrieval.py`) is the platform's own
  retrieval path, exposed at `POST /v1/corpus/documents`, `POST /v1/rag/ingest`
  and `POST|GET /v1/rag/query`.

`vendor/**` is sealed and read-only here; fixing them is a Store-side change.

## Persistence

Persistence is route-scoped: the route writes the request with the tenant's
`store.save()` after the kernel reports success. Handlers dispatch blocks and
never persist, so a failed block can never leave a row behind.

## Authorship

Every module under `app/actions/` carries the WRITER stamp
(`Written by the factory WRITER role (codewhale exec)`).
