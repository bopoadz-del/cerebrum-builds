# DentalDesk Clinic Manager

A practice-management platform for a four-person dental practice: patient
visits with tooth-level procedure and fee detail, the front desk's appointment
book, the day-before email reminder run, a patient register, and searchable
per-patient clinical history. Receptionists own scheduling; clinicians own the
visit and treatment records.

It runs standalone. There is no Store URL, no cloud model provider and no
outbound HTTP at runtime: every capability dispatches into the blocks vendored
under `vendor/blocks/`, and persistence is a local sqlite file on
`STORAGE_PATH`.

## Capabilities

| capability | binds | persistence entity |
| --- | --- | --- |
| `patient_visit_records` | capture, database, validation, audit | `patient_visit_records` |
| `appointment_scheduling` | workflow, database, validation, audit | `appointment_scheduling` |
| `todays_appointment_list` | dashboard, database, workflow | `todays_appointment_list` |
| `day_before_email_reminders` | notification, queue, event_bus, audit | `day_before_email_reminders` |
| `patient_directory` | database, capture, validation | `patient_directory` |
| `clinical_history_search` | database, analytics | `clinical_history_search` |
| `role_based_access` | team, audit | `role_based_access` |

## Run it

```sh
pip install -r requirements.txt -r requirements-dev.txt
export STORAGE_PATH=./data           # sqlite lives here (Alembic owns the schema)
export PLATFORM_TOKEN=dev-local-token
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`GET /health` is fail-closed: process, disk, database and Alembic head are
measured, and a missing disk or a revision behind head is not a green badge.

## HTTP surface

| route | meaning |
| --- | --- |
| `GET /health` | fail-closed health contract |
| `GET /` | operator console (HTML) |
| `GET /v1/jobs`, `/v1/catalog`, `/v1/inventory`, `/v1/capabilities`, `/v1/gates`, `/v1/provenance` | kernel job roster and live readers |
| `POST /v1/<capability>` | create one record (bearer token required) |
| `GET /v1/<capability>` | list this tenant's records (filter/sort/page) |
| `GET /v1/<capability>/{id}` | read one record (404 for another tenant) |
| `PUT /v1/<capability>/{id}` | update one record |
| `DELETE /v1/<capability>/{id}` | delete one record |
| `GET /v1/retrieval?q=…` | tenant-scoped search of the practice's own records |
| `POST /v1/authority/resolve` | precedence.v1 resolution over ranked claims |

Capability writes require the bearer token; missing required fields and invalid
enumerations are HTTP 422; a missing token is HTTP 401.

## Tenancy

One tenant per request, always. The tenant is resolved from the authenticated
principal (`PLATFORM_TOKEN`, plus `TENANT_TOKENS` for extra clinics) and never
from a client-supplied name. Every capability row carries `tenant_id`, and a
cross-tenant read answers 404 rather than 403 so existence never leaks.

## Test it

```sh
python scripts/release_gate.py     # pytest -m "not pilot" + provenance
python -m pytest tests             # the full suite, including pilot cases
python scripts/acceptance.py       # ≥12 measured store-green checks
```

`tests/` splits into a code-phase suite (imports, dispatch, models, routes) and
`@pytest.mark.pilot` cases that require the blocks to accept a schema-valid
payload end to end.

## Layout

| path | what lives there |
| --- | --- |
| `app/main.py` | FastAPI app factory, lifespan (Alembic upgrade), `/health` |
| `app/models.py` | one dataclass per capability (`FIELDS`, `CONSTRAINTS`) |
| `app/actions/<capability>.py` | one handler per capability, `handle(payload)` |
| `app/routes.py`, `app/routers/` | HTTP surface over the actions |
| `app/store.py` | tenant-scoped sqlite persistence (schema from Alembic) |
| `app/dispatch.py` | in-process block dispatch over `vendor/blocks/` |
| `app/block_inputs.py` | block-contract input construction |
| `app/tenancy.py`, `app/security.py`, `app/auth.py` | tenant + token boundary |
| `app/authority.py` | precedence.v1 |
| `app/formulas.py` | safe arithmetic for fee totals and reminder dates |
| `app/retrieval.py` | tenant-scoped corpus search |
| `app/llm.py` | deterministic offline text composer (no provider wired) |
| `alembic/versions/` | versioned schema (0001 baseline, 0002 lifecycle audit) |
| `frontend/` | operator console (command center, intake chat, runtime truth) |

## Deploy

`Dockerfile` builds the image (it runs `scripts/release_gate.py`, so a red
suite cannot produce a deployable image) and `render.yaml` describes the
service. Migration runs from `scripts/entrypoint.sh` against the mounted disk
before serving.
