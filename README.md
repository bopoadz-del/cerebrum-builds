# CallOps

An outbound AI voice-calling platform for a real-estate brokerage, built first
for **PSI**. It ingests brokerage lead files, queues and paces dials against
calling windows and caps, pitches real project numbers retrieved from ingested
project sheets under a **cite-or-refuse** discipline, qualifies each
conversation into a fixed three-outcome vocabulary with the collected fields,
and hands warm leads to a human broker through a **whispered summary and
conference bridge**. Every call event is written down and reconstructable per
Call SID.

Offline by contract: no Store callbacks, no cloud LLM, no outbound HTTP except
the one connector the operator configures. Every Store block is vendored into
this repository and executed in-process. The Twilio edge is **stubbed** until a
real account and caller number exist, and CI never dials.

## Run it

```sh
python -m pip install -r requirements.txt -r requirements-dev.txt

# local
export STORAGE_PATH=./data              # the one persistence root
export PLATFORM_TOKEN=dev-local-token   # bearer token the API requires
uvicorn app.main:app --port 8000        # migrations run at boot
```

`GET /` serves the operator console (paste the token, pick a capability, send).
The console is `app/static/index.html`: dependency-free, no bundler, and the
one UI the platform serves. It discovers the capabilities from
`GET /v1/capabilities`, drives them against the real routes, and renders the
authority label (`label` / `authority_label`, precedence.v1) beside every
answer. `frontend/` is the same console in React components: the image builds
and type-checks it into `/app/frontend-dist` and CI builds it on every commit,
so it is built source rather than dead source — but it is not a second UI on
`/`.
`GET /health` is fail-closed: process, persistent disk, database, Alembic head
and the settings the platform needs are each reported, and a failure answers
503. `GET /metrics` serves request counts and latency.

```sh
python -m pytest tests                  # the whole suite
python -m pytest tests -m "not pilot"   # code-phase suite
python scripts/acceptance.py            # the floor, in-container
python scripts/bench.py                 # p95 under load
```

OpenAPI is committed at `docs/openapi.json`.

## Settings — set these before you rely on them

**Money.** The brief named no country, no currency and no broker commission, so
none is assumed. Every rule that needs one refuses by name until the operator
sets it:

| Setting | Required | Meaning |
| --- | --- | --- |
| `CURRENCY` | **yes, before any price or commission** | ISO code the brokerage prices in. No default. `POST /v1/qualification_and_broker_summary` still records the qualification; the commission maths refuses. |
| `BROKER_COMMISSION_PERCENT` | **yes, before a commission** | Commission on a closed deal. No default. |
| `TAX_RATE_PERCENT` | optional | Tax/VAT on a quoted price. No default; when unset no total is produced. |

**Pacing.** These are the brokerage's own caps; the stated defaults are a
starting point, not an assumption:

| Setting | Default | Meaning |
| --- | --- | --- |
| `DAILY_CALL_CAP` | 200 | Calls per day per campaign. |
| `CONCURRENCY` | 3 | Simultaneous dials. |
| `LOCAL_DRIVE_ROOT` | `STORAGE_PATH` | The one root the file capabilities may touch. |

**Tenancy.** `PLATFORM_TOKEN` owns the default tenant. `TENANT_TOKENS`
(`"token:tenant,token:tenant"`) binds more: PSI is a tenant, and a second
brokerage is a row, not a rebuild. Reads are tenant-scoped without exception:
a record belonging to another tenant answers **404**, never 403 and never the
row. A caller who presents a principal this deployment does not know is not
folded into the operator's tenant — it resolves to its own empty namespace, so
an unknown bearer reads nothing and cannot write at all (`/v1` writes answer
401 without a bound token).

**The broker leg.** `BROKER_TRANSFER_NUMBER` is the human broker's line for a
warm transfer. It is read from the environment with **no default** — the
platform does not choose a broker line on the brokerage's behalf. Set it (or
send `broker_number` on the `warm_transfer` record) before a transfer; with
neither, the transfer is recorded as `declined` with the setting named in
`blocker` rather than dialled somewhere invented.

**The Twilio edge.** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` and
`TWILIO_CALLER_NUMBER` are read from the environment with **no defaults**. With
all three set the gateway performs a real REST originate; with any of them unset
it is stubbed against the recorded fake-Twilio fixtures in
`tests/fixtures/twilio/` and refuses to open a socket.

**Other connectors.** `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` /
`SMTP_PASSWORD` / `NOTIFY_FROM` turn the notification block's mail channel on.
`GOOGLE_REFRESH_TOKEN` + `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` (or
`GOOGLE_ACCESS_TOKEN`) turn the Google Drive connector on. Without them the
capability stays `drive_mode: stubbed` and says so. The `google_drive` entity
declares those three credential settings as fields, so a record may carry them
(the connector then reports `credentials_supplied_with_record`); they are
stored with the record so the capability round-trips its own schema, and they
are treated as credential material everywhere else — never logged, never
echoed by `/health`, and never used to dial out unless the same names are set
in the process environment.

## Capabilities

| Capability | What it does | Blocks |
| --- | --- | --- |
| `lead_intake_and_dial_queue` | Parses a lead file into lead records and holds a paced dial list | capture, queue, formula_executor, validation |
| `call_state_machine` | The call lifecycle keyed to the Call SID, with the call window as a guard | workflow, orchestrator, event_bus |
| `project_knowledge_grounding` | Answers price / payment-plan / handover questions from ingested project sheets, cite-or-refuse | knowledge, vector_search, ingestion_provenance, evidence_or_refuse, llm_enhancer |
| `voice_gateway` | Twilio Programmable Voice: originate, ASR gather in en/ar, Polly Neural TTS, status callbacks mapped onto transitions | event_bus |
| `warm_transfer` | Summary → broker leg → whisper (broker only) → conference bridge | event_bus |
| `qualification_and_broker_summary` | The three-outcome schema and the structured broker summary | validation, recommendation_template, knowledge |
| `outcome_capture_and_ledger` | Every call event ledered, archived and state-synced per Call SID | audit_chain, database, storage, agent_state_sync |
| `crm_destination_placeholder` | **Placeholder**: records the CRM push intent and shape, pushes nothing | mock_connector_bus, webhook |
| `notification` | Pings the broker / sales channel the moment a lead qualifies | notification, event_bus |
| `local_drive` | Confined local file surface for lead files and project sheets | local_drive |
| `google_drive` | **Stubbed** connector until credentials exist | google_drive |
| `mcp_adapter` | Reads the block catalogue (lists and describes; never invokes) | mcp_adapter |

Every capability has `POST /v1/{capability}`, `GET /v1/{capability}`,
`GET /v1/{capability}/{id}`, `PUT /v1/{capability}/{id}` and
`DELETE /v1/{capability}/{id}`.

## The three outcomes are a schema, not prose

```
outcome ∈ { project_interested, other_re_interested, not_interested }
collected: property_type, budget, area, timeline
```

`outcome` is enforced by the model and by the route guard: a fourth value is
refused with HTTP 422. The handoff is decided by the vocabulary
(`project_interested → warm_transfer`, `other_re_interested →
send_alternative_projects`, `not_interested → close_and_suppress`), never by a
model's mood.

## Cite or refuse

`project_knowledge_grounding` answers only from the tenant's ingested project
sheets. A claim about a price, a payment plan or a handover date that the
corpus cannot support is **withheld**, and the record says so
(`grounded: false`, `withheld_reason`). Ingest a sheet through
`POST /v1/rag/ingest` (or drop it in `local_drive`) and the same question is
answered with a citation and its authority label.

Authority layers are versioned data in `app/authority_ladder.v1.json`
(`precedence.v1`): 1 certified > 2 documents > 3 formulas > 4 procedures. The
model is told which layer wins; it never chooses, and every answer carries the
label.

## Known limits (named, not hidden)

`docs/blockers.json` is the register: the `knowledge` block cannot load in this
delivery's runtime slice, the Google Drive connector is stubbed for want of
credentials, the MCP adapter cannot enumerate the lazy registry it is handed,
and the CRM destination is a placeholder because no destination was named.
Each affected capability records `blocks_unavailable` by name and takes the
path that does run — it never reports a block as answered.

Twilio is stubbed by design: no account and no caller number were supplied.
`tests/fixtures/twilio/` holds the recorded webhook fixtures the gateway and
the transfer are verified against.

## Docker

```sh
docker build -t callops .
docker run -p 8000:8000 -v callops-data:/app/data callops
```

The image builds the React console (a `node:18-slim` stage that runs
`npm install`, `tsc --noEmit` and `vite build`, shipping the bundle at
`/app/frontend-dist`), runs `scripts/release_gate.py` (a red suite does not
produce a deployable image), applies migrations on boot via
`scripts/entrypoint.sh`, and answers `/health` before traffic. The console it
serves at `/` is `app/static/index.html`, deliberately untouched by that build:
one UI is served, and it is the one the pilot harness drives.
`render.yaml` describes the same service for Render.
