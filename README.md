# CallOps

Outbound AI voice calling for a real-estate brokerage (PSI). CallOps ingests
brokerage lead files, paces dials against calling windows and caps, pitches
real project numbers retrieved from ingested project sheets under a
**cite-or-refuse** discipline, qualifies each conversation into a fixed
three-outcome vocabulary, and hands warm leads to a human broker through a
whispered summary and a conference bridge. Every call event is written to a
hash-chained ledger, and the dashboard reports attempted / answered / interest
split / transfers / conversion per campaign.

Tenancy is first class: PSI is a tenant, and a second brokerage is a row, not a
rebuild.

---

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

export STORAGE_PATH=./data          # the platform's one storage root
python -c "from app.migrations import upgrade_head; upgrade_head()"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or run exactly what the image runs — migrations, then the server, on the same
port the deploy will use:

```bash
STORAGE_PATH=./data PORT=8000 sh scripts/entrypoint.sh
```

* Console: <http://localhost:8000/>
* Health (fail-closed): `GET /health` — 503 when the disk, the database or the
  migrations are not ready.
* Metrics: `GET /metrics` — request counts and latency.
* API description: `docs/openapi.json` (committed, and asserted equal to the
  routes the app actually serves).

### Docker

```bash
docker build -t callops .
docker run --rm -p 8000:8000 \
  -e PORT=8000 \
  -e APP_ENV=production \
  -e PLATFORM_TOKEN=... -e PLATFORM_TOKEN_B=... \
  -e STORAGE_PATH=/app/data \
  -v callops-data:/app/data \
  callops
curl -sf http://127.0.0.1:8000/health
```

The build is two stages. The first compiles the React tree in `frontend/`
(`npm ci` against the committed lockfile, `npx tsc --noEmit`, `npx vite
build`) and its bundle is copied to `/app/frontend-dist`, which `app/main.py`
mounts at `/console`. The second installs `requirements.txt` and
`requirements-dev.txt` — the dev requirements are there on purpose, because
the image runs the release gate below — and serves the dependency-free
console at `/`.

Boot is `ENTRYPOINT` → `scripts/entrypoint.sh`: `alembic upgrade head`, then
`exec uvicorn` on `$PORT` (default 8000). A migration failure refuses to start
rather than serving traffic against a schema it never applied. The image's
`HEALTHCHECK` probes `http://127.0.0.1:$PORT/health`, and `/health` is
fail-closed (503 until the disk is writable, `platform.db` opens and alembic
is at head), so a container cannot be reported ready before its migrations
have run. Hosts that assign a port (Render) set `PORT`; both uvicorn and the
probe follow it.

### Deploy it

**Render** — `render.yaml` is the reference: Docker runtime, one service,
`healthCheckPath: /health`, one 1 GB disk mounted at `/var/data`
(`STORAGE_PATH=/var/data`, `BACKUP_DIR=/var/data/backups`). Supply every
`sync: false` variable in the dashboard. `APP_ENV=production` is set for you
and is what makes the platform refuse to boot on the public development
tokens.

**Buildpack / Procfile host** — `web: sh scripts/entrypoint.sh`. The
entrypoint resolves the repository root from its own path, so it runs from a
slug, a container or a checkout.

**Any container host** — the image is self-contained; mount a volume at
`STORAGE_PATH` and set the settings below. `docs/deploy.json` records the
health checks, the backup path, the rollback drill and the single point of
failure.

### Operate it

```bash
scripts/backup.sh /var/data/backups   # SQLite online backup; pg_dump when DATABASE_URL is set
scripts/rollback.sh rev-n baseline    # writes the record and prints the env the restart needs
python scripts/release_gate.py        # layout, packaging, console, models, boot, openapi, suite
python scripts/bench.py               # p95 over 200 concurrent /health requests
```

* **Backups** go to `BACKUP_DIR`, else `STORAGE_PATH/backups` — the same disk
  as the database, so they protect against logical loss, not disk loss. A
  backup nobody restored is a file, not a backup:
  `tests/test_backup_restore.py` restores what `scripts/backup.sh` produces.
  The SQLite leg uses the `sqlite3` CLI when it is installed and the Python
  stdlib's online backup API otherwise, so it works in the image (which ships
  python, not the CLI). With `DATABASE_URL` set it needs `pg_dump` on the
  host: the image does not ship one, and the script says so instead of
  writing a file that is not a dump.
* **Rollback** is a restart with `APP_REVISION` (and `APP_MARK`) set, because
  `app/revision.py` reports those two from the environment.
  `scripts/rollback.sh` writes the on-disk record and prints the restart
  environment; on Render, roll back the deploy (same disk, schema stays at
  head). Persisted rows are never wiped by either.
* **Upgrading** is a redeploy: migrations run on boot. A red suite cannot
  become a deployable image — the build runs the release gate.

---

## Settings the operator MUST set before real use

The brief deliberately does not state a country, a currency or any rate. This
platform does not invent them, so these have **no default** and the paths that
need them refuse by name (`CURRENCY is not set …`):

| Setting | Required before | Why |
|---|---|---|
| `APP_ENV=production` | serving real traffic | the switch that refuses to boot on the public development tokens (`validate_boot`); any other value leaves `dev-local-token` live as the platform token |
| `CURRENCY` | quoting a price, recording a budget, commission | the brief states no country or currency |
| `VAT_RATE` | `formulas.price_with_tax` | no tax rate is stated in the brief |
| `BROKER_COMMISSION_RATE` | `formulas.broker_commission` | no commission is stated in the brief |
| `PRICE_CURRENCY_TOKENS` | finding a price sentence in a retrieved sheet, e.g. `AED,QAR` | optional: the price lane looks for `CURRENCY` plus whatever you name here, and assumes no other currency |
| `DEFAULT_COUNTRY_CODE` | dialling a number stored without a country code | otherwise the lead is **held**, never guessed |
| `PLATFORM_TOKEN` (+ `PLATFORM_TOKEN_B`, `TENANT_TOKENS`, `TENANT_NAMES`) | serving traffic | development defaults are public knowledge; `APP_ENV=production` refuses to boot on them |
| `PLATFORM_TENANT` (+ `PLATFORM_TENANT_B`) | naming whose rows these are | the defaults are `local` / `psi-partner-b`; the brokerage's own rows must be filed under the tenant id the operator chooses |
| `TENANT_PHONE_NUMBERS` | a Twilio webhook, which carries no bearer token | the called number is the principal (`"+10000000000:psi"`); an unmapped number falls back to `PLATFORM_TENANT`, never to a name in the form |
| `TENANT_PERMISSIONS` | a read-only brokerage | per-tenant permissions (`"psi:read+write+process,other:read"`); a write from a read-only tenant is refused |
| `STORAGE_PATH` | any persistent state | the platform's one storage root; in the image it is `/app/data`, on Render `/var/data` on the mounted disk |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_CALLER_NUMBER` | placing a real call | no Twilio credentials were supplied |
| `TWILIO_ANSWER_URL`, `TWILIO_STATUS_CALLBACK_URL` | receiving the carrier's TwiML fetch and status callbacks | settings, never request fields: without them the edge cannot be driven by real callbacks |
| `TWILIO_ALLOW_DIALING=1` | placing a real call | an explicit opt-in so a test run or CI can never dial |
| `BROKER_TRANSFER_NUMBER` | warm transfer | without it a transfer is recorded `declined`, never claimed |
| `SALES_CHANNEL_WEBHOOK` (or `BROKER_ALERT_WEBHOOK`, `NOTIFY_WEBHOOK_URL`) | the broker ping and the live-connector proof | the platform's one real outbound delivery |
| `EGRESS_ALLOWLIST` | a webhook on a private or self-hosted host | egress is refused unless the host is public or named here |
| `CRM_DESTINATION` | activating the CRM placeholder | the brief names no CRM |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REFRESH_TOKEN` / `GOOGLE_DRIVE_FOLDER_ID` | reading Drive | no Drive credentials were supplied |
| `GOOGLE_ALLOW_API=1` | reading Drive | the same explicit opt-in as `TWILIO_ALLOW_DIALING`: credentials alone still call nothing |
| `LLM_PROVIDER` + `LLM_API_KEY` | model-authored dialogue | without them the deterministic grounded planner runs |

`DATABASE_URL` is optional: unset means one SQLite file at
`STORAGE_PATH/platform.db` (the reference deployment); set, it is the
operator's Postgres and `pg_dump` is needed for `scripts/backup.sh`.

Operator-owned values **with documented defaults** (change them, they are
yours): `DAILY_CALL_CAP=250`, `CONCURRENCY=3`, `DIAL_INTERVAL_SECONDS=30`,
`MAX_ATTEMPTS=3` (the brief's ceiling), `RETRY_BACKOFF_MINUTES=45`,
`RETRY_BACKOFF_FACTOR=2.0`, `CALL_WINDOW_START` / `CALL_WINDOW_END` (the
single-window fallback; the per-language windows below are what the dialer
uses), `CALL_WINDOW_EN`, `CALL_WINDOW_AR`,
`CALL_WINDOW_TZ`, `CALL_WINDOW_DAYS`, `CONFERENCE_BRIDGE_TIMEOUT_SECONDS=45`,
`WEBHOOK_TIMEOUT_SECONDS=8`, `RETRIEVAL_TOP_K=4`, `RETRIEVAL_MIN_SCORE=0.05`,
`CHUNK_CHARACTERS=900`, `CHUNK_OVERLAP=120`, `AUTH_RATE_WINDOW_S=60`,
`AUTH_RATE_MAX=20`, `MCP_TOOL_SCOPE=platform`, `LLM_MODEL`, `LLM_BASE_URL`,
`TWILIO_VOICE_EN`, `TWILIO_VOICE_AR`, `TWILIO_API_BASE`, `LOCAL_DRIVE_ROOT`,
`BACKUP_DIR`, `APP_REVISION` / `APP_MARK` (what `/health` reports, and what a
rollback restarts with), `SENTRY_DSN` (off unless set *and* `sentry-sdk` is
installed), `PRODUCT_NAME` / `PRODUCT_ID`.

`.env.example` lists every setting with a comment. `GET /v1/settings` reports
which are set (never their values).

---

## What is real, and what is a named blocker

Marked placeholders — each **declares** what it is missing instead of
pretending (`GET /v1/connectors` shows the live state):

| Capability | State | Blocker it names |
|---|---|---|
| `voice_gateway` (Twilio edge) | stubbed | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_CALLER_NUMBER`, `TWILIO_ALLOW_DIALING`. Originate returns the exact request it would send; the TwiML, ASR languages, Polly voices and all seven status callbacks are built and certified against the fake harness in `tests/fixtures/`. |
| `crm_destination_placeholder` | placeholder | `CRM_DESTINATION`. It records the outcome, the broker summary and the exact payload shape a connector would send, and claims no delivery. |
| `google_drive` | stubbed | the four Drive settings. The OAuth refresh + Drive v3 request sequence is implemented and tested against a fake transport; it makes no call without credentials *and* `GOOGLE_ALLOW_API=1`. |
| `llm` | deterministic by default | `LLM_PROVIDER`, `LLM_API_KEY`. The model path is implemented (real completion request) and its draft passes the same grounding check as the deterministic one: a figure the retrieved evidence does not contain is withheld, not spoken. |

Working for real: lead-file intake and the durable dial queue, the call state
machine with its window guard, retrieval and cite-or-refuse over ingested
project sheets, qualification and the structured broker summary, the
hash-chained ledger, the notification connector (a real HTTPS POST through the
private-address guard — the platform's one live outbound round trip, provable
with `POST /v1/connectors/webhook/probe`), the tenant-scoped local drive, the
MCP adapter, the dashboard and the formulas.

The reads behind the console are surfaces in their own right, not just the
writes' shadow: `GET /v1/leads/import` (which file became which rows, and what
held the rest), `GET /v1/rag/ingest` (the provenance of every ingested sheet:
source, project, digest, certification), `GET /v1/rag/query` (the same
retrieval as the POST, addressed by query string) and `GET /v1/rag/ground`
(cite-or-refuse posture — per project, which liability claims the corpus can
carry and which will be withheld on the live call, `?project_tag=` to narrow
it), `GET /v1/ledger/verify` (walk every hash chain in the tenant, or one
`?call_sid=`; an empty ledger verifies). Each answers with its authority label
and refuses an unbound token.

---

## Layout

```
app/main.py                 app factory: observability, routers, health, lifespan migrations
app/routes.py               the /v1/<capability> envelope (validate → handle → save)
app/routers/                domain surfaces: retrieval, voice, leads/queue, dashboard, platform
app/actions/<capability>.py one handler per capability, CAPABILITY_ID + handle(payload)
app/models.py               the twelve entities: FIELDS, CONSTRAINTS, from_dict/to_dict
app/store.py                tenant-scoped persistence on one root, routed through app.db
app/db.py                   the backend switch: DATABASE_URL → Postgres, else SQLite
app/tenancy.py              token → tenant, resolved from the principal only
app/security.py             egress guard, path guard, reserved keys, redaction
app/authority.py            precedence.v1: certified > documents > formulas > procedures
app/formulas.py             caps, pacing, backoff, windows, metrics, money
app/retrieval.py            tenant-scoped corpus; cite-or-refuse
app/llm.py                  dialogue turns (deterministic, or model + grounding check)
app/domain.py               the domain kernel: intake, transitions, ledger, summary, metrics
app/voice.py                the Twilio edge behind one contract, stubbable and fake-testable
app/dispatch.py             the blocks CallOps composes, dispatched in process
alembic/versions/0001_baseline.py      one table per capability, tenant_id on every table
alembic/versions/0003_conversation_corpus.py  work_queue, idempotency, rag_documents, rag_chunks
tests/                      the suite (see below)
```

## Tests

```bash
python -m pytest -m "not pilot" -q     # the code-phase gate
python -m pytest -q                    # plus the pilot cycle
python scripts/release_gate.py         # what the image runs before it is published
python scripts/bench.py                # p95 over 200 concurrent requests, budget 500ms
```

The suite covers, per capability: a valid record persisting and reading back,
another tenant's read answering **404**, missing required fields and
out-of-vocabulary values answering **422**, malformed payloads never reaching
500, the state machine refusing a skipped step, a ledger tamper being detected,
the transfer sequence with and without a broker number, the recorded Twilio
callbacks driving the routes and the ledger, RAG plant → retrieve → withhold, a
real webhook round trip on loopback, the money formulas refusing by name when
the operator has not stated a currency, and every route the console calls.

## Tenancy and authority

* One tenant per request, always. The tenant is resolved from the bearer token
  (`app/tenancy.py`); a payload that names its own tenant is refused with 422,
  and another tenant's record answers 404 — never 403, never the row.
* A **write** always requires a token bound to a tenant (401 without one). A
  **read** uses the read posture in `app/tenancy.read_tenant`: identical in a
  multi-tenant deployment, and in a single-tenant deployment (no
  `PLATFORM_TOKEN_B`, no `TENANT_TOKENS`) the deployment's own tenant, which is
  what lets the console and the platform's own probes read the queue they run.
  A token that is presented and unknown is refused 401 either way. Binding a
  second operator token or any `TENANT_TOKENS` entry makes reads demand a
  principal exactly like writes — that is the switch, and it is stated here
  rather than left implicit. `GET /v1/settings` reports the posture.
* `precedence.v1` ranks layers **certified > documents > formulas >
  procedures**. Every answer carries the winning layer, a label per claim and a
  divergence record where two layers disagree; a claim no layer supports is
  withheld and named.
