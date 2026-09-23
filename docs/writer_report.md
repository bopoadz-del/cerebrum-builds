# CallOps — WRITER pass report (pilot cycle)

Product: **CallOps** (`real_estate`) — outbound AI voice-calling platform for the PSI brokerage.
Tree: this checkout, staged and verified in place before commit.

## What this pass did

The pilot-cycle WRITER pass started on an empty staging checkout whose destination
already carried the code-cycle tree. This pass re-landed that tree, verified it against
the factory's own judges (not the tree's own tests alone), audited it with three
read-only specialists (BACKEND, DEVOPS/SECURITY, FRONTEND), and fixed every defect
those audits found that a gate or the brief can see.

### Fixes that matter

| # | Where | Defect | Fix |
|---|-------|--------|-----|
| 1 | `app/health.py` | **Blocker.** `/health` required `<STORAGE_PATH>/platform.db` to exist and probed it with `sqlite3.connect`. With `DATABASE_URL` set nothing creates that file, so the container was 503 forever and `docker_health_200` / `postgres_boot_200` could never pass. | Health probes the connection `app/store.py` actually uses, through `app/db`; `platform.db` is required only on the SQLite path. |
| 2 | `app/voice.py` | The private broker whisper was emitted as a sibling of a nested `<Dial>` in the **lead's** document, so the lead heard the summary; and neither party joined the same conference, so the "bridge" was two half-calls. | `dial_broker_twiml` is the broker-leg document (private whisper, then the shared conference); `caller_leg_twiml` carries the conference and never the whisper. `tests/test_voice_harness.py` now asserts both. |
| 3 | `app/actions/warm_transfer.py` | The whisper was built from the boolean `qualified`, which rendered as `Outcome True`, and never read the qualification record. | The summary is structured from the qualification record loaded by Call SID (request fields win) and speaks the fixed three-outcome vocabulary. |
| 4 | `app/routers/voice_routes.py`, `app/routers/leads_routes.py` | `DAILY_CALL_CAP` was advertised in the pacing answer and enforced nowhere: no originate ever wrote a countable attempt, and the queue processor dialled without the window/cap guard (and passed the reserved word `action`). | Originate persists the attempt through the route's tenant-scoped save; the queue processor answers to the same guard, writes `voice_action`, and advances `attempt_count` toward the brief's ceiling of 3. |
| 5 | `app/routers/voice_routes.py` | Twilio's speech `<Gather>` callback carries no `Language`, so an Arabic caller was always answered with the English withheld line. | The call's language comes from the voice-edge row for its Call SID; an explicit form value still wins. |
| 6 | `app/routers/dashboard_routes.py`, `app/static/index.html` | The brief's per-campaign metric list was not complete at the route, and the console never showed it. | `/v1/metrics/campaigns` rows carry attempted, answered, the three-outcome interest split (zero-filled), transfers and conversion; the console renders that table with its authority badge. |
| 7 | `tests/test_domain_flows.py` | The three defects above had no counter-test. | New tests: per-campaign metric list, whisper confidentiality/bridge, structured-from-record whisper, cap counting. |

### Verification (measured on this tree)

- `python -m pytest -m "not pilot" -q` → **267 passed, 2 skipped, 4 deselected**
- `python -m pytest -m pilot -q` → **4 passed**
- `python scripts/acceptance.py` (host-side) → **16/21**; the five that do not measure
  here (`docker_health_200`, `postgres_boot_200`, `one_live_connector`,
  `backup_restore_roundtrip`, `bench_p95`) are measured by the Store gate inside the
  built image and are named, not skipped silently.
- Factory judges run against this tree: `writer_behaviour` **ok, 0 findings**
  (every capability fails closed when its blocks fail), `ui_end_to_end` **ok**
  (12 capabilities driven, every console route answers), one-record round-trip
  **12 round-tripped / 0 failed / 0 unjudged**, `persist_round_trip_errors` empty.
- Independent end-to-end domain probe over the booted app (26 assertions): lead CSV →
  dial queue with cap/pacing, RAG ingest → query with provenance and a withheld claim
  for a project the corpus does not carry, whisper in Polly Hala/ar-SA to the broker
  leg only, status callbacks mapped per Call SID, ledger chain intact, CRM connector
  marked stubbed.

## Known limits (named, not hidden)

- Twilio credentials and caller number are unset, so the voice edge ships **stubbed**:
  no call is placed, and every stubbed answer names the settings it is missing.
- The CRM destination is unstated, so `crm_destination_placeholder` records intent and
  shape and declares `blocks_unavailable: ["CRM_DESTINATION"]` — no delivery is claimed.
- Country, currency and every tax rate are operator settings with **no default**, listed
  in `README.md`; the brief states none and the platform chooses none.
- `Dockerfile`/`render.yaml` are render-ready, not deployed: the Store gate measures the
  image and restart survival on the build box.

Written by the factory WRITER role (codewhale exec)
