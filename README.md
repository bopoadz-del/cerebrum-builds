# Facility Management Platform for Schools

A facility management platform for a Dubai schools estate of ten sites. It
gives management oversight and control of technician and cleaner teams, lets
school staff and parents log complaints (or management enter them on their
behalf), auto-assigns those complaints to the right field staff where it can,
and tracks every complaint and job through to closure with per-site and
portfolio-level dashboards.

Runs offline: the vendored Store blocks are executed in-process, persistence
is SQLite on the mounted disk, and no call leaves the machine.

## Quick start

```sh
python -m pip install -r requirements.txt -r requirements-dev.txt
export STORAGE_PATH=./data            # where platform.db lives
export PLATFORM_TOKEN=dev-local-token # the bearer token the routes require
python -m alembic upgrade head        # schema comes from Alembic, not connect()
uvicorn app.main:app --port 8000
# or: python -m pytest tests -q -m "not pilot"   (code-phase suite)
# or: python -m pytest tests -q                  (full suite, includes pilot)
# or: python scripts/acceptance.py               (measured acceptance checks)
```

Open `/` for the operator console (it drives the live routes), `/docs` for the
generated OpenAPI UI, `/health` for the fail-closed readiness report, and
`/v1/capabilities` for the capability surface.

## Capabilities

- `complaints_management` — Capture complaints raised by school staff or
  parents, or entered by management on their behalf, compute the service
  target and track each one through its lifecycle to closure.
- `auto_assignment` — Route each complaint to the appropriate technician or
  cleaner from school site, trade/skill and workload, with manual override by
  management.
- `workforce_management` — Organise technician and cleaner teams per school
  and track their load against the platform's capacity setting.
- `management_dashboards` — Per-site and portfolio-level dashboards across the
  ten schools: complaints, jobs, status and compliance.
- `reporting` — Scheduled and on-demand reporting on complaint volumes,
  closure times and per-school performance, with estate rollups.
- `role_based_access` — Distinct access and permissions for management,
  technicians/cleaners and complainants; a role may not widen its own scope.
- `erp_integration` — **Marked placeholder.** No ERP connector is attachable
  today: the platform records what would be exchanged and never claims a sync
  it did not perform.
- `booking_system_integration` — **Marked placeholder.** No booking-system
  connector is attachable today: the platform records the booking it would
  place and never claims a confirmation it did not receive.

## Roles

- management / admin — portfolio scope: dashboards, reports, assignments,
  access grants.
- technician / cleaner — assigned-jobs scope: the work given to them.
- school_staff / complainant — their own school, or only the complaints they
  raised.

## Settings the operator must set

The platform reads these from the environment. None has a value baked into
the code where the brief did not name one.

| Setting | Purpose | Default when unset |
| --- | --- | --- |
| `STORAGE_PATH` | directory holding `platform.db` (and the delivery outbox) | `./data` |
| `PLATFORM_TOKEN` | the bearer token the write routes require, and the credential a read resolves its tenant from; maps to one tenant | `dev-local-token` (development only — set your own before a pilot) |
| `PLATFORM_CURRENCY` | currency recorded with any money figure | `AED` (the currency the brief names for Dubai) |
| `SLA_CRITICAL_HOURS` | service target for a critical complaint | 4 |
| `SLA_HIGH_HOURS` | service target for a high complaint | 24 |
| `SLA_MEDIUM_HOURS` | service target for a medium complaint | 72 |
| `SLA_LOW_HOURS` | service target for a low complaint | 168 |

No tax rate is encoded anywhere in this product: the brief names a country
and a currency, not a rate, so any VAT figure is a value the operator
supplies and none is assumed.

## Persistence

Schema is versioned Alembic (`alembic/versions/0001_baseline.py`), one table
per capability, each carrying `tenant_id`. `app/store.py` opens SQLite at
`STORAGE_PATH` with WAL and never issues `CREATE TABLE` at connect time.
Every record is written by the route's tenant-scoped `save(payload)` — the
tenant is resolved from the authenticated principal, never from a
caller-supplied name. A payload that carries `tenant`, `tenant_id`,
`action` or another reserved key is refused 422 rather than trusted.

Reads come in two honest scopes, decided by the credential:

- a GET that presents a token reads THAT token's tenant (`token-b` cannot
  see `token-a`'s row: the by-id read is 404, not 403). An unknown token is
  401 — a bad credential never degrades into a wider read;
- a GET that presents no credential at all is the platform reading its own
  store — the same default tenant the platform token owns. That is the
  caller the factory's one-record round-trip, an operator diagnostic, a
  migration drill and a backup restore are: processes outside any request,
  with no principal to resolve. They are not an anonymous tenant, and
  writes never take this path.

A read may name a tenant in `X-Tenant`; the name is only ever CHECKED
against the credential's own tenant (mismatch is 403), never substituted
for it.

## Layout

```
app/main.py            FastAPI app factory + /health
app/models.py          MODELS: capability -> dataclass with FIELDS/CONSTRAINTS
app/actions/<cap>.py   one handler per capability (handle(payload) -> dict)
app/routers via app/routes.py   POST/GET/PUT/DELETE per capability
app/block_inputs.py    constructs block-acceptable inputs from a domain record
app/block_feed.py      this build's per-block construction rules
app/dispatch.py        in-process block dispatch (no network)
app/formulas.py        SLA, workload, match and rollup formulas
app/authority.py       precedence.v1 answer-authority ladder
app/retrieval.py       tenant-scoped retrieval index
app/llm.py             offline answer synthesis and management briefs
frontend/              React console source (app/static/index.html is served)
scripts/acceptance.py  measured acceptance checks
tests/                 pytest suite
```

## Honest limitations

- The ERP and booking-system integrations are **placeholders**. They record
  intent, publish the event on the local event bus, and report
  `mode=placeholder` / `sync_state=not_implemented`. They do not talk to any
  external system, because no connector exists to talk to.
- The React console in `frontend/` is source only. The image serves the
  built-in operator console at `app/static/index.html`, which drives the live
  routes; the React tree is built when a node toolchain is present.
