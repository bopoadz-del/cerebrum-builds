# DevOps review — CallOps (`product_id` real-estate)

Hat: *a DevOps team receives this and must deploy it without its author.*

Reviewed: `Dockerfile`, `.dockerignore`, `Procfile`, `render.yaml`,
`.github/workflows/ci.yml`, `scripts/entrypoint.sh`, `scripts/backup.sh`,
`scripts/rollback.sh`, `scripts/bench.py`, `scripts/release_gate.py`,
`README.md`, `docs/deploy.json`, `docs/data_lifecycle.json`, and
`frontend/vite.config.ts` (claimed: the bundle has to be *servable* at
`/console`, which is what the Dockerfile promises).

`app/` and `tests/` were frozen for a parallel verification and were not
edited; defects found there are reported in §3 instead. Note that a parallel
agent **was** editing `app/` (last write 18:34:29Z) during this review, so the
verification timestamps below matter: the final gate run at 18:36:18Z is after
that write.

---

## 1. What was run, and what came back

### 1.1 Tooling available here (raw)

```
$ which docker
which-docker-exit=1                     # docker is NOT installed on this machine
$ which sqlite3
which-sqlite3-exit=1                    # sqlite3 CLI is NOT installed on this machine
$ which curl node npm python3
/usr/bin/curl
/usr/bin/node
/usr/bin/npm
/usr/local/bin/python3
$ python3 -V; node -v; npm -v
Python 3.11.16
v18.20.4
9.2.0
$ ls alembic/versions
0001_baseline.py
0002_lifecycle_audit.py
0003_conversation_corpus.py
```

So: the image cannot be built here. Nothing in this review claims a
`docker build`.

### 1.2 Fresh venv, the dependencies the image installs

```
$ python3 -m venv /tmp/callops-devops-venv \
  && /tmp/callops-devops-venv/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt
pip-exit=0
$ /tmp/callops-devops-venv/bin/python -c "import fastapi, starlette, uvicorn, alembic, sqlalchemy; ..."
fastapi 0.141.1 | starlette 1.6.0 | uvicorn 0.53.0 | alembic 1.20.0 | sqlalchemy 2.0.54
```

`requirements.txt` + `requirements-dev.txt` install clean, so the floors in
`requirements.txt` (`fastapi>=0.141`, `starlette>=1.6`, `psycopg[binary]>=3.1`,
`setuptools>=83.0.0`) resolve to real releases.

### 1.3 The image boot, simulated without docker

Exactly what `ENTRYPOINT` runs, in the fresh venv, against an **empty**
throwaway `STORAGE_PATH`, on port **8931** (a port of my own). `$PORT` was
never bound or probed, port 8000 was never used, and the process was stopped
by the exact PID captured at start (`kill $APP_PID` only — no
`pkill`/`killall`/`fuser`).

```
$ STORE=$(mktemp -d /tmp/callops-store-XXXXXX)          # STORE=/tmp/callops-store-JhZoyD (empty)
$ PATH=/tmp/callops-devops-venv/bin:$PATH PORT=8931 STORAGE_PATH="$STORE" sh scripts/entrypoint.sh > /tmp/callops-entrypoint.log 2>&1 &
APP_PID=19068
--- entrypoint log (migrations, then uvicorn)
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_baseline, Baseline schema for CallOps: one table per capability.
INFO  [alembic.runtime.migration] Running upgrade 0001_baseline -> 0002_lifecycle_audit, v2 schema change: lifecycle_audit table (up and down).
INFO  [alembic.runtime.migration] Running upgrade 0002_lifecycle_audit -> 0003_conversation_corpus, Work queue, idempotency keys and the project-sheet corpus.
{"event": "entrypoint.start", "revision": "", "storage": "/tmp/callops-store-JhZoyD", "port": "8931"}
INFO:     Started server process [19068]
INFO:     Waiting for application startup.
--- GET /health
http_code=200
{"ok":true,"status":"ok","checks":[{"name":"process","ok":true,"detail":"pid=19068"},
 {"name":"persistent_disk","ok":true,"detail":"/tmp/callops-store-JhZoyD"},
 {"name":"database","ok":true,"detail":"/tmp/callops-store-JhZoyD/platform.db"},
 {"name":"migrations","ok":true,"detail":"current=0003_conversation_corpus head=0003_conversation_corpus"}],
 "revision":"rev-n","mark":"baseline"}
--- GET /metrics
http_code=200
--- GET / (dependency-free console)
http_code=200
--- GET /console/ (React bundle: only exists after the image COPY)
http_code=404
--- store created by boot
-rw-r--r-- 1 appuser 1000 159744 platform.db
--- stopping ONLY pid 19068
stopped pid 19068
```

Second cold boot, with a `STORAGE_PATH` whose leaf directory **did not exist**
(`/tmp/callops-boot2-r8nKjJ/nested/data`) — the path the entrypoint has to
create before the health check can pass:

```
APP_PID=20136
health http_code=200
{"ok":true,"status":"ok","checks":[{"name":"process","ok":true,"detail":"pid=20136"},
 {"name":"persistent_disk","ok":true,"detail":"/tmp/callops-boot2-r8nKjJ/nested/data"},
 {"name":"database","ok":true,"detail":"/tmp/callops-boot2-r8nKjJ/nested/data/platform.db"},
 {"name":"migrations","ok":true,"detail":"current=0003_conversation_corpus head=0003_conversation_corpus"}], ...}
{"event": "entrypoint.start", ..., "storage": "/tmp/callops-boot2-r8nKjJ/nested/data", "port": "8931"}
stopped pid 20136
```

`/console/` is 404 **here on purpose**: the React bundle is a build artefact
that only exists after the image's `COPY --from=console /ui/dist
/app/frontend-dist`. §1.4 proves the bundle is built and is addressed at
`/console/assets/*`.

### 1.4 The healthcheck command the image runs, executed verbatim

The `HEALTHCHECK` line was extracted from the Dockerfile and run against the
running container-equivalent, with `$PORT` set to the port the entrypoint had
bound, plus a negative control:

```
$ CMD=$(grep -A1 "^HEALTHCHECK" Dockerfile | tail -1 | sed 's/^ *CMD python3 -c "//; s/"$//')
HEALTHCHECK CMD = python3 -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health', timeout=2)"
app running as pid 22301 on the port it took from PORT
$ PORT=8931 python3 -c "$CMD"; echo exit=$?
healthcheck-CMD with PORT=8931 exit=0 (0 = the probe answered)
$ PORT=9999 python3 -c "$CMD"; echo exit=$?
negative control with PORT=9999 exit=1 (non-zero = the probe really follows PORT)
stopped pid 22301
```

### 1.5 The frontend stage

```
$ npm ci --no-audit --no-fund                 # npm-ci-exit=0; added 68 packages
$ npx tsc --noEmit                            # tsc-exit=0
$ npx vite build --outDir dist --emptyOutDir  # vite-exit=0
vite v5.4.21 building for production...
✓ 35 modules transformed.
dist/index.html                   0.41 kB │ gzip:  0.27 kB
dist/assets/index-mvQIC1Su.css    1.47 kB │ gzip:  0.68 kB
dist/assets/index-CP6ku3iL.js   151.38 kB │ gzip: 48.64 kB
✓ built in 3.40s
$ grep -o 'src="[^"]*"\|href="[^"]*"' dist/index.html
src="/console/assets/index-CP6ku3iL.js"
href="/console/assets/index-mvQIC1Su.css"
```

Both console assets are built, and they are addressed at `/console/assets/*`
— which is where `app/main.py` mounts the bundle.

### 1.6 Release gate, benchmark, scripts, documents

```
$ date -u
2026-09-21T18:36:18Z
$ python scripts/release_gate.py            # (app/ last written 18:34:29Z, before this run)
ok [layout]
ok [console]
ok [packaging]
    (no frontend-dist here: the React console is not built in this tree)
ok [bundle]
ok [models]
ok [boot]
ok [openapi]
ok [suite]
RELEASE GATE: all checks passed
release-gate-exit=0
$ python scripts/bench.py
requests=200 p50=195.3ms p95=283.0ms budget=500ms
STORE_BENCH_P95_MS=283.0
bench-exit=0
$ python -c "import json;[json.load(open(p)) for p in ('docs/deploy.json','docs/data_lifecycle.json','docs/blockers.json','docs/openapi.json')];print('json ok')"
json ok
$ sh -n scripts/entrypoint.sh && echo "sh -n entrypoint ok"
sh -n entrypoint ok
$ bash -n scripts/backup.sh scripts/rollback.sh && echo "bash -n ok"
bash -n backup+rollback ok
$ python -m py_compile scripts/release_gate.py scripts/bench.py && echo "py_compile ok"
py_compile ok
$ python -c "import yaml;yaml.safe_load(open('.github/workflows/ci.yml'));print('ci.yml parses')"
ci.yml parses
```

`scripts/backup.sh` smoke, on a runner **without** the `sqlite3` CLI (so this
exercises the new stdlib fallback), dump then read back:

```
$ STORAGE_PATH="$TMP/data" bash scripts/backup.sh "$TMP/backups"
/tmp/callops-backup-CmJ8/backups/platform-20260921T183453Z.db
backup-exit=0
-rw-r--r-- 1 appuser 1000 8192 platform-20260921T183453Z.db
rows in the dump: [('a1',)]
```

`scripts/rollback.sh` smoke:

```
$ STORAGE_PATH="$TMP2" sh scripts/rollback.sh rev-n baseline
{"event":"rollback.performed","revision":"rev-n","storage":"/tmp/callops-rollback-8OIE"}
rollback.sh: restart the process with APP_REVISION=rev-n APP_MARK=baseline (Render: roll back the deploy; same disk, same schema at head)
rollback-exit=0
$ cat "$TMP2/deploy_revision"
rev-n
```

### 1.7 The operator-settings cross-check (README vs `app/` vs `.env.example`)

Every environment variable read anywhere in `app/` was extracted with an AST
scan (`os.environ[...]`, `os.environ.get`, `os.getenv`, `config.env`,
`require_text`/`require_rate`/`require_float`), then checked against
`README.md` and `.env.example`:

```
env names read in app/: 53
NOT in README: []                        # after the README fix in §2 row 15
NOT in .env.example: ['CALL_WINDOW_END', 'CALL_WINDOW_START', 'MCP_TOOL_SCOPE',
                      'NOTIFY_WEBHOOK_URL', 'PRODUCT_ID', 'PRODUCT_NAME', 'TWILIO_API_BASE']
```

Before the fix the gap was:
`['CALL_WINDOW_END', 'CALL_WINDOW_START', 'TENANT_PERMISSIONS',
'TENANT_PHONE_NUMBERS', 'TWILIO_ANSWER_URL', 'TWILIO_STATUS_CALLBACK_URL']`.

And the three settings the brief refuses to let anyone invent, checked in every
place a default could hide:

```
$ grep -rn "CURRENCY\|VAT_RATE\|BROKER_COMMISSION_RATE" app/ --include=*.py
app/config.py:26-28  UNSET_BY_BRIEF = ("CURRENCY", "VAT_RATE", "BROKER_COMMISSION_RATE")
app/config.py:114    return require_text("CURRENCY", "pricing, budgets and broker commission")
app/config.py:118    return require_rate("VAT_RATE", "tax applied to a quoted price")
app/config.py:122    return require_rate("BROKER_COMMISSION_RATE", "commission owed on a closed deal")
$ grep -n "CURRENCY\|VAT_RATE\|BROKER_COMMISSION_RATE" .env.example
9:CURRENCY=     10:VAT_RATE=     11:BROKER_COMMISSION_RATE=        # all three empty
$ grep -n -A1 "CURRENCY\|VAT_RATE\|BROKER_COMMISSION_RATE" render.yaml Dockerfile
render.yaml:28-33   sync: false  (no value)  ×3
```

No default is invented for them anywhere: not in `app/`, not in `.env.example`,
not in `render.yaml`, not in the Dockerfile.

### 1.8 Secrets

```
$ ls -la .env
ls: cannot access '.env': No such file or directory
$ find . -name "*.pem" -o -name "*.key" ...
(no output)
$ grep -n "^\.env$\|^data$\|^frontend/node_modules$\|^frontend/dist$" .dockerignore
7:.env   23:data   44:frontend/node_modules   45:frontend/dist
```

No `.env`, key or certificate in the tree; what is in the tree cannot reach a
layer. Credentials arrive from the platform environment only.

---

## 2. Defects found and fixed

Each is silent in the happy path and expensive in a deploy.

| # | File | Defect | Fix | How it was verified |
|---|---|---|---|---|
| 1 | `Dockerfile` | `HEALTHCHECK` probed a hardcoded `127.0.0.1:8000` while `ENTRYPOINT` binds `${PORT:-8000}`. Every container host (Render included) assigns `PORT`, so the probe would hit a closed port: a perfectly healthy container would be reported unhealthy and never receive traffic. | The probe reads `PORT` (default 8000); `--start-period` 20s → 40s to cover the migrations applied before uvicorn binds. | §1.4: the HEALTHCHECK command exits 0 with `PORT=8931` and 1 with `PORT=9999`. |
| 2 | `frontend/vite.config.ts` | Vite's default `base` is `/`, so the bundle asked for `/assets/index-*.js` while `app/main.py` mounts it at `/console`: the page would load and then 404 its own JavaScript and CSS. Confirmed against the committed build output — `frontend/dist/index.html` contained `src="/assets/index-CP6ku3iL.js"`. | `base: "/console/"`, and `check_console_bundle` in the release gate now fails the build if any non-http `src`/`href` is not under `/console/`. | §1.5: a real rebuild now emits `/console/assets/index-CP6ku3iL.js` and `/console/assets/index-mvQIC1Su.css`. |
| 3 | `Dockerfile` | The console stage ran `npm install` without copying `frontend/package-lock.json`: the asset served was whatever the registry resolved on build day, not what the repository pins. | Copy the lockfile, use `npm ci`. | §1.5: `npm ci` exits 0 (68 packages). |
| 4 | `scripts/entrypoint.sh` | `cd /app` — but the same script is the `Procfile` web command, where the root is the slug/repo, not `/app`. On a buildpack host the boot dies at `cd`. | Resolve the root from the script's own path (`dirname "$0"/..`). | §1.3 (boot from a checkout, cwd-independent); `sh -n` clean. |
| 5 | `scripts/entrypoint.sh` | Nothing created `STORAGE_PATH`. On the SQLite path alembic does; with `DATABASE_URL` set (a declared backend) nothing does — and `/health`'s `persistent_disk` check fails on a missing directory, so a correctly migrated Postgres deploy answers **503 forever**. | `mkdir -p "${STORAGE_PATH:-./data}"` before migrating. | §1.3 second boot: a store path whose leaf did not exist became healthy. (The Postgres leg itself is unverified here — §4.) |
| 6 | `scripts/backup.sh` | The SQLite leg required the `sqlite3` CLI, which `python:3.12-slim` does not ship: the documented backup path did not exist in the deployed image. | Falls back to the stdlib `sqlite3.Connection.backup()` — same API as `app/backup.py`, same file format, **no new dependency**. A missing `pg_dump` on the Postgres leg is now named and exits 2 instead of writing something that is not a dump. | §1.6: on a runner with no `sqlite3` CLI the script exits 0 and the dump reads back `[('a1',)]`. |
| 7 | `scripts/backup.sh` | Default output was `./backups` (caller's cwd) while `app/backup.py` defaults to `STORAGE_PATH/backups`, and the documented `BACKUP_DIR` setting was ignored: script and app disagreed about where backups live. | `"${1:-${BACKUP_DIR:-${STORAGE_PATH:-./data}/backups}}"`. | §1.6 (`BACKUP_DIR`/`STORAGE_PATH` resolution path exercised). |
| 8 | `scripts/rollback.sh` | It wrote `STORAGE_PATH/deploy_revision` and exited 0, but `app/revision.py` reports `APP_REVISION`/`APP_MARK` **from the environment** — so the "rollback" changed no observable revision while printing a success line. | Prints the restart environment on stderr and states that the schema is not downgraded (boot applies `upgrade head`). `app/` is frozen, so the marker file cannot be made authoritative from here — §3. | §1.6: stdout JSON unchanged, stderr now carries `APP_REVISION=rev-n APP_MARK=baseline`, `deploy_revision` written. |
| 9 | `.github/workflows/ci.yml` | Nothing in CI ever built or booted the image: a Dockerfile that bundled nothing, probed the wrong port or failed to migrate would pass CI. | New `image` job: `docker build` (which runs the release gate inside the build), boot on `PORT=8931`, probe `/health`, `/metrics`, `/`, `/console/`, then wait for the image's own `HEALTHCHECK` to report `healthy` and fail if it does not. Added `permissions: contents: read`. The existing `python -m pytest tests` line is untouched (the store gate reads it). | `ci.yml parses` (§1.6). The job itself runs on a runner — §4. |
| 10 | `render.yaml` | `APP_ENV` was never set, so a production deploy ran as `development`, where `validate_boot` does **not** refuse the public development tokens: an operator who left `PLATFORM_TOKEN` blank would serve traffic on `dev-local-token`. | `APP_ENV: production` (fail-closed) and `BACKUP_DIR: /var/data/backups` so backups land on the mounted disk. | Config read in §1.7; no deploy performed — §4. |
| 11 | `scripts/release_gate.py` | The docstring claimed it checks "the committed OpenAPI document matches the routes actually served"; no such check existed. There were no packaging checks at all. | Added `check_openapi_matches_served`, `check_packaging` (entrypoint is `ENTRYPOINT`; a console stage exists and bundles; the bundle is copied into the image; the entrypoint migrates **before** serving; the healthcheck follows `$PORT` and probes `/health`; `.dockerignore` excludes `.env`, `data`, `frontend/node_modules`), and `check_console_bundle` (bundle ⇒ `index.html` + assets, all URLs under `/console/`). Docstring and check list now match the code. | §1.6: gate prints `ok [packaging]`, `ok [bundle]`, `ok [openapi]`, exit 0. |
| 12 | `.dockerignore` | `COPY . .` had no `.env` rule: an operator's `.env` (real tokens) would be baked into a layer and survive deleting the file. Local databases, editor state and caches were copied in too. | `.env`, `.env.local`, `.env.*.local`, `*.pem`, `*.key`, `data`, `backups`, `*.db*`, `.pytest_cache`, `.mypy_cache`, `.codewhale`, `frontend/dist`, `docs/writer_*.log`, … (`.env.example` deliberately kept: no values, and the release gate reads it). | §1.8. |
| 13 | `Dockerfile` | The build-time release gate left its artefacts in the image (`/app/data/platform.db`), so a deploy that forgot to mount a volume would quietly serve a database from build time. | `RUN python3 scripts/release_gate.py && rm -rf /app/data && mkdir -p /app/data`. | Inspection + §1.3 (the runtime root is created and migrated on boot). |
| 14 | `scripts/bench.py` | The bench defaulted `STORAGE_PATH` to `<repo>/data`, migrating and writing into the checkout it measures. | Defaults to a fresh temp directory; an explicit `STORAGE_PATH` still wins. | §1.6: p95 283.0ms, and no `data/` churn is needed to run it. |
| 15 | `README.md` | The must-set table omitted settings that are read in `app/` and a deploy needs: `APP_ENV=production` (the switch that refuses the dev tokens), `PLATFORM_TENANT`/`PLATFORM_TENANT_B`, `TENANT_PHONE_NUMBERS`, `TENANT_PERMISSIONS`, `TWILIO_ANSWER_URL`, `TWILIO_STATUS_CALLBACK_URL`, `EGRESS_ALLOWLIST`, `GOOGLE_ALLOW_API`, `STORAGE_PATH`; and the defaults list omitted `CALL_WINDOW_START`/`CALL_WINDOW_END`, `BACKUP_DIR`, `APP_REVISION`/`APP_MARK`, `CONFERENCE_BRIDGE_TIMEOUT_SECONDS`, `WEBHOOK_TIMEOUT_SECONDS`, `MCP_TOOL_SCOPE`, `RETRIEVAL_MIN_SCORE`, `LLM_MODEL`/`LLM_BASE_URL`, `TWILIO_VOICE_EN`/`TWILIO_VOICE_AR`, `TWILIO_API_BASE`, `LOCAL_DRIVE_ROOT`, `SENTRY_DSN`, `PRODUCT_NAME`/`PRODUCT_ID`, and the `NOTIFY_WEBHOOK_URL` alias. Added a Deploy/Operate section too: the `$PORT` contract, the two-stage build, migrations on boot, the Render reference, backups, rollback, release gate and bench. | §1.7: `NOT in README: []`. |
| 16 | `docs/deploy.json` | Claimed the rollback drill is `tests/test_deploy.py + factory test_deploy_observe.py`; **no `tests/test_deploy.py` exists in this tree** (file listing confirmed), so the document described a drill nobody can run from here. It also said nothing about the healthcheck, backups, packaging or CI. | The drill now names what exists (`scripts/rollback.sh` + `app/revision.py`, and the factory's `deploy_observe` exercise), and new `packaging`, `backups`, `ci` and `health.probe` sections record the real contract and the real evidence. | `json ok`; file listing. |
| 17 | `docs/data_lifecycle.json` | Named `tests/test_data_lifecycle.py` as the restore drill (file does not exist) and listed the migrations as `0001_baseline`, `0002_lifecycle_audit`, omitting `0003_conversation_corpus.py` which is in the tree. | Now names `tests/test_backup_restore.py` and lists all three revisions. | `json ok`; `ls alembic/versions`; §1.3 shows 0003 applying. |

The brief's two-stage property is preserved: the dependency-free console
(`app/static/index.html`) is still served at `/`, and the React bundle is still
built in the console stage and served at `/console`.

## 3. Defects found and reported, not fixed (outside my write scope)

* `app/config.py` reads `CALL_WINDOW_START` / `CALL_WINDOW_END`, but neither
  `.env.example` nor README documents them (both document only `CALL_WINDOW_EN`
  / `CALL_WINDOW_AR`, which is what the dialer uses). `app/` and
  `.env.example` are outside my scope. An operator who sets
  `CALL_WINDOW_START` gets the documented default and no warning. (Listed in
  the README defaults list now, which is the most I can do from here.)
* `app/revision.py` ignores `STORAGE_PATH/deploy_revision`. Either the marker
  file should be read there, or `scripts/rollback.sh` should not appear to
  change the revision (it no longer does — see §2 row 8). The real fix is in
  frozen `app/`.
* The image runs as **root**. A non-root `USER` is standard hardening, but the
  Render disk is mounted for the container user and `/health` fails closed on a
  non-writable storage root; changing it without being able to test the mount
  here would risk the deploy. Recorded in `docs/deploy.json` as a follow-up.
* `EXPOSE 8000` is documentation only (the bound port is `$PORT`). Left as-is:
  it matches the entrypoint's default, and the healthcheck change makes the
  runtime port explicit.
* Environment noise observed, not mine to touch: `tests/test_formulas_authority.py`
  is a 0-byte file alongside `tests/test_formulas_and_authority.py` (a parallel
  agent's in-flight artefact). It collects no tests and does not affect the
  image; flagging it so the receiving team does not wonder.
* No GitHub Actions job can validate `render.yaml` here (no Render account or
  token), and the image is not built on this box: the new CI `image` job is the
  first end-to-end execution of the Dockerfile.

## 4. Blockers — what could NOT be verified here, and why

| Blocker | Consequence |
|---|---|
| `docker` is not installed (`which docker` → exit 1, raw output in §1.1) | No `docker build`, no `docker run`, so the Dockerfile's `COPY --from`, `HEALTHCHECK` and `ENTRYPOINT` instructions have never been executed *by Docker* here. What was executed instead is §1.3–1.5. The CI `image` job is the first full execution. |
| `sqlite3` CLI not installed (`which sqlite3` → exit 1) | The CLI branch of `scripts/backup.sh` is unverified; the stdlib fallback branch is what ran (§1.6). Both produce the same SQLite file format. |
| No `pg_dump`, no Postgres server, no `DATABASE_URL` deployment | The Postgres leg of the backup and the Postgres boot path are unverified. The script refuses by name when `pg_dump` is missing. |
| No Render account, registry or credentials | `render.yaml` was reviewed by inspection only; no deploy was performed and none is claimed. |
| No GitHub remote/runner | `.github/workflows/ci.yml` parses, but the new `image` job has never run. |
| A parallel agent was editing `app/` during this review (last write 18:34:29Z) | Every result above is timestamped; the final gate run (18:36:18Z) is after that write. If `app/` changes again, the gate must be re-run — a red suite is supposed to stop the deploy, and the image re-runs the gate at build time. |
| The shared checkout was write-locked by that peer for part of this task | `bash` was refused with *"cannot prove a bounded file target or read-only execution while peers are writing in this shared checkout (blocking peers: agent_4ea881d2)"*. Retrying cleared it; nothing in §1 was run before the lock cleared, and nothing that was not run is claimed. |

## 5. What the receiving DevOps team has to do

1. `docker build -t callops .` — if this passes, the console stage bundled
   (type-checked), the release gate ran the suite inside the build, and both
   assets are in the image.
2. Supply the settings README lists as operator-required. `APP_ENV=production`
   is what makes the platform refuse to boot on the development tokens;
   `CURRENCY`, `VAT_RATE` and `BROKER_COMMISSION_RATE` have **no default
   anywhere** by design (§1.7).
3. Mount a volume at `STORAGE_PATH` (`/var/data` on Render). Migrations run on
   boot; a migration failure refuses to start rather than serving an
   unmigrated schema.
4. Trust the health probe, not the process: `/health` is 503 until the disk is
   writable, `platform.db` opens and alembic is at head, and the image's
   `HEALTHCHECK` follows `$PORT` (§1.4).
5. `scripts/backup.sh <dir>` on a schedule, and restore it once. Same-disk
   backups do not survive disk loss (`docs/deploy.json` SPOF).
6. Roll back by restarting with `APP_REVISION`/`APP_MARK` (or Render's deploy
   rollback); the schema is not downgraded.
