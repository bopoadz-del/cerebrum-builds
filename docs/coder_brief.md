FACTORY CODING-AGENT BRIEF (one prompt — this is the product story)

You are manufacturing a full pilot repo, not a thin scaffold.

Exit condition — the run is DONE only when ALL of these are true:
- the PRODUCT gate passes (pytest -m pilot on the booted product)
- the STORE gate passes
- the ledger records pilot_ready=true
- the level grade is STORE_GREEN or FOUNDING_CUSTOMER_READY

Three gates (fail-closed; a gate that did not run is NOT a pass):
- CODE → CODE_GREEN: the code-phase suite (pytest -m "not pilot") — imports, routes, handlers
- PRODUCT → STORE_GREEN (with STORE): post-boot: the pilot-marked tests against the booted product, and a one-record round-trip per capability (POST creates, GET returns it)
- STORE → FOUNDING_CUSTOMER_READY when founding files + contracts hold: scripts/acceptance.py (≥12 measured checks) inside the Store-built Docker image — k/k required; restart-survival of the booted store; authorship floor is not acceptance

CODE_GREEN (code-cycle SUCCESS, pilot_ready=false) is a prototype, not Finished.
Do not treat templates-only output, stub handlers, skipped capabilities, or
pilot_ready=false as a finished product. Thin SUCCESS is a failure to finish.

Contracts you must honour on every capability you write:
- Blocks are action-dispatched. Pass action= as a keyword, never inside the
  payload dict. Prefer action=BLOCK_DEFAULT_ACTIONS.get(block_id).
- Call execute() for EVERY id in BLOCK_IDS. A declared block that is never
  invoked fails the WRITER behaviour gate and halts the build.
- Validate only the capability's own fields. Construct block inputs; do not
  demand block-specific keys (topic, sql/table, file paths, team_id,
  channel, steps) from the caller. The execute wrapper synthesizes those
  from the domain record. If you require a field, type, or vocabulary,
  declare it on the spec — the factory copies handler contracts onto the
  spec so the pilot suite can build a payload you will accept. Do not
  invent a second, stricter contract the spec cannot express.
- Offline platform: no network, no HTTP store callbacks, channel "mcp" only.
- WRITER gate writer_behaviour POSTs a payload built from each capability's own FIELDS + CONSTRAINTS (allowed_values[0], status=open, channel=email, generic str='sample'). Every handler must accept that payload. Declaring a stricter contract than the spec produces 'no capability accepted its own schema'.
- REUSE keep-path handlers must accept a schema-sample POST. Populate BLOCK_DEFAULT_ACTIONS from block.json / the factory Store map (including formula_executor, vector_search, capture, spec_analyzer, storage, and estate_registry) and pass action= as a keyword (action=BLOCK_DEFAULT_ACTIONS.get(block_id)). execute() with action=None is 'Unknown action: None'. Workflow step_0 without step.action is workflow: step_0 (event_bus): error. Store workflow reads input['result'] — a schema-sample POST that omits it fails as "workflow: RuntimeError: 'result'". Photographed roster: patient_records_management, appointment_scheduling, prescription_management, billing_and_invoicing, client_communication_portal.
- PRODUCT one-record round-trip POSTs a schema-sample payload then re-reads store.list_all(entity) and GET /v1/{capability_id}. A miss is 'did not remember a record they were given'. Every capability must persist that record to its alembic entity via store.save(ENTITY, payload) (factory-grounded persist). Keyword-fallback veterinary_care_core, audit, dashboard are persistable capabilities.
- PRODUCT test_every_capability_route_accepts_payload POSTs a schema-sample payload then runs bound blocks. A capability that binds workflow + event_bus (appointment_scheduling) must prepare EACH event_bus step including Store step_0, step_1 and step_2+ (block=event_bus, action=publish, topic, payload dict, message, channel=mcp, tool=event_bus) — never forward the raw sample as 'input': payload. Exact shape: {"block": "event_bus", "action": "publish", "input": {"topic": "<str>", "payload": {}, "message": "<str>", "channel": "mcp", "tool": "event_bus"}}.
- Fail-closed auth HotelOps H: claimed_actor only (client actor/user_id is not identity); CORS allowlist refuses `*`.
- Never edit sealed paths: vendor/**, vendor_blocks/**, vendor_blocks_mirror/**, blocks.lock.json, build_ledger.jsonl, .git/**. Call Store blocks via execute(action=...). Do not patch vendor. formula_executor is Store-listed but not vendored in this platform — do not invent the module; compute dose/invoice math in app/domain.py.

This brief is the horizon. Recovery session `sess_69f28c0d8bc540e9` (PATHS_VIOLATED after vendor/** + build_ledger.jsonl). Start from main tip that includes airport PR #11 and REPLACE all airport/retail product code with veterinary-care.

# C-BRIEF TEMPLATE
revision: 2026-09-13
owner_shape: veterinary_care
fill: deterministic (registry + block.json + domain pack + intake blueprint)
llm_writes_brief: never
session_id: sess_69f28c0d8bc540e9
product_id: veterinary-care
product_name: Veterinary Care Platform / VetCare Hub

==================================================
TARGET
==================================================

Booted veterinary_care platform: Veterinary Care Platform (VetCare Hub).
A clinic-operations hub for veterinary practice operators. It centralizes
patient charts, appointment slots, prescriptions, invoices, and client
messages so a small clinic can run a pilot without a full PIMS.

Who it is for: clinic operators
Roles: operator, admin

Capabilities (photographed keyword-fallback roster — use these ids):
- veterinary_care_core [REUSE]: persist entity  blocks=['analytics']
- patient_records_management [REUSE]: dual-registered  blocks=['knowledge', 'vector_search', 'memory']
- appointment_scheduling [REUSE]: workflow + event_bus (prepared step_0/1/2 + result)  blocks=['workflow', 'event_bus', 'notification', 'queue']
- prescription_management [REUSE]: hole-fill  blocks=['validation', 'analytics']  (formula_executor not vendored — domain dose math)
- billing_and_invoicing [REUSE]: hole-fill  blocks=['validation', 'notification', 'queue']  (formula_executor not vendored — domain invoice math)
- client_communication_portal [REUSE]: dual-registered  blocks=['notification', 'event_bus', 'knowledge']
- audit [REUSE]: persistable when bound  blocks=['audit']
- dashboard [REUSE]: persistable when bound  blocks=['dashboard', 'analytics']

==================================================
CUT 1 — STEP 0 INVENTORY + STOP
==================================================

Coder: list what the Store already provides. REUSE by exact block id, verified present — flag missing, never assume.

Vendored in this platform (vendor.cerebrum.blocks._BLOCK_DEFS): analytics, audit, capture, dashboard, document_engine, event_bus, file_hasher, knowledge, memory, notification, queue, recommendation_template, storage, team, validation, vector_search, workflow

Store registry (exact ids, verified listed): analytics, audit, capture, dashboard, database, document_engine, estate_maintenance, estate_registry, event_bus, evidence_verifier, file_hasher, formula_executor, knowledge, memory, notification, portfolio_rollup, queue, readiness_engine, recommendation_template, spec_analyzer, storage, team, validation, vector_search, workflow

REUSE (verified present AND vendored — emit handler source):
- veterinary_care_core: REUSE ['analytics'] — emit app/actions/veterinary_care_core.py
- patient_records_management: REUSE ['knowledge', 'vector_search', 'memory'] — emit app/actions/patient_records_management.py
- appointment_scheduling: REUSE ['workflow', 'event_bus', 'notification', 'queue'] — emit app/actions/appointment_scheduling.py (prepared event_bus steps)
- prescription_management: REUSE ['validation', 'analytics'] — emit app/actions/prescription_management.py
- billing_and_invoicing: REUSE ['validation', 'notification', 'queue'] — emit app/actions/billing_and_invoicing.py
- client_communication_portal: REUSE ['notification', 'event_bus', 'knowledge'] — emit app/actions/client_communication_portal.py
- audit: REUSE ['audit'] — persistable capability — emit app/actions/audit.py
- dashboard: REUSE ['dashboard', 'analytics'] — persistable capability — emit app/actions/dashboard.py

GAPS (you author; do not invent a block id):
- (none)

MISSING claimed REUSE (do not bind — not vendored in this platform):
- formula_executor (Store-listed; no vendor.cerebrum.blocks.formula_executor)
- database (Store-listed; not in _BLOCK_DEFS)
- readiness_engine, estate_maintenance, estate_registry, evidence_verifier, spec_analyzer, portfolio_rollup

WORK ITEMS (C-BRIEF hole-fill; GENERATE gaps plus REUSE that still need handlers):
- veterinary_care_core: REUSE hole-fill — persist / BLOCK_DEFAULT_ACTIONS / clinic load score
- patient_records_management: REUSE hole-fill — vector_search keyword action=search
- appointment_scheduling: REUSE hole-fill — prepared event_bus step_0, step_1, step_2 + result
- prescription_management: REUSE hole-fill — domain daily_dose_mg (not persist stub 0)
- billing_and_invoicing: REUSE hole-fill — domain invoice total (not persist stub 0)
- client_communication_portal: REUSE hole-fill — MCP notify envelope
- audit: REUSE hole-fill — persist one record to entity audit
- dashboard: REUSE hole-fill — persist one record to entity dashboard

CUT 1 is read-only. Stop after this inventory. Do not build yet.


==================================================
CUT 2 — RUNNER VALIDATE
==================================================

CUT 2 — runner validates ids against the vendored registry (not the coder).
Claimed REUSE that is not present HALTS before WRITER build.
Verified present: analytics, knowledge, vector_search, memory, workflow, event_bus, notification, queue, validation, audit, dashboard
Missing (flagged, not bound): formula_executor, database


==================================================
CUT 3 — BUILD (DO)
==================================================

C-BRIEF / FACTORY_CODE_CLI owns this workspace even when STEP 0 is 100% REUSE.
Bind and write real handlers for every capability — deepen REUSE (persist,
constructed block inputs, BLOCK_DEFAULT_ACTIONS, prepared event_bus steps).
Do not re-implement a verified Store block from scratch — bind the registry-verified ids.
Every verified REUSE row must emit a loadable app/actions/{capability_id}.py.
Invocation contracts: pass action= as a keyword, never inside the payload dict.
Prefer action=BLOCK_DEFAULT_ACTIONS.get(block_id).
Call execute() for EVERY id in BLOCK_IDS.
Call execute() from app.dispatch only. Do not import app.actions, app.routes, or app.main from a handler.
The factory owns app/actions/__init__.py — do not rewrite it with eager re-exports.
If you assign a block, you feed it — construct block inputs; do not demand block-specific keys from the caller.
Envelope status vocabulary (schema-enforced): open | in_progress | closed.

Sampling rules (must match writer_behaviour probe _value):
- CONSTRAINTS.allowed_values[0] when declared
- status / *_status → open
- channel / *_channel → email (never the word sample)
- datetime / *_at / *_datetime → 2026-09-03T10:00:00
- date / *_date → 2026-09-03
- time / *_time → 10:00:00
- email-shaped names → sample@example.com (writer) / guest@example.com (PRODUCT)
- int/float → min if set else 1 (min=0 samples as 0)
- bool → false
- otherwise the word sample

Every capability's model already carries this envelope; the gate
POSTs it plus samples for any extra FIELDS you declare:
{"reference": "sample", "status": "open"}

appointment_scheduling MUST emit factory-grounded prepared event_bus steps
for step_0, step_1, and step_2. Workflow input MUST include result.
Do not execute("workflow", payload) with the raw schema sample.

factory-grounded persist:
- every capability has an alembic 0001 table named spec.entity
- store.COLUMNS and store.save use that same entity
- handle() persists via store.save(ENTITY, payload) after blocks succeed (ok_envelope)
- do not persist to 'records' or a capability id that is not the entity
- PRODUCT isolates STORAGE_PATH

Keyword-fallback persistable capabilities:
  veterinary_care_core, audit, dashboard
Each must remember one record.

HotelOps A (domain kernel, not persist stub):
- open × walk_in clinic_load_score = 0.45 (not 1.0)
- overloaded below 0.6
- prescription daily_dose_mg from weight × mg/kg (never silent 0)
- invoice subtotal + tax + total from invoice_kind (consult base 85.00, tax 8%)
- appointment cascade next_action + sla_minutes
- claimed_actor only; Principal actor is operator/admin

Launching-ready full-pilot authorship floor: emit ≥5 keepable agent-written
app/actions/*.py handlers. This roster is 8.

# PHASE 1 of 3 — BACKEND (DO)
Write routes, handlers, schema, domain kernel, alembic entities.
Every required capability gets a one-record POST/GET round-trip.
STOP / checkpoint after PHASE 1 acceptance.

# PHASE 2 of 3 — FRONTEND + RAG (DO)
UI on the working backend (frontend modules call the live POST/GET routes).
HARD WRITE app/rag_routes.py: quoted POST /v1/rag/ingest and GET|POST /v1/rag/query
plus /v1/steward/rag/* twins.
STOP / checkpoint after PHASE 2 acceptance.

# PHASE 3 of 3 — INTEGRATION + RENDER-READY (DO)
Package, boot, and integration: Dockerfile + render.yaml + app/main.py.
Bind HTTP to 0.0.0.0:$PORT. Ephemeral filesystem — persist under STORAGE_PATH.
render-ready is not live Render deploy and not Store Docker acceptance.

Domain pack (binding fields):
{
  "authoritative_calculations": [
    "clinic_load_score = STATUS_SCORE[status] * WINDOW_WEIGHT[caseload_window]",
    "daily_dose_mg = weight_kg * mg_per_kg (defaults 10 kg × 5 mg/kg when envelope omits numbers)",
    "invoice_total = kind_base + round(kind_base * 0.08, 2)"
  ],
  "core_business_workflows": [
    "one-record round-trip for veterinary_care_core",
    "one-record round-trip for patient_records_management",
    "one-record round-trip for appointment_scheduling",
    "one-record round-trip for prescription_management",
    "one-record round-trip for billing_and_invoicing",
    "one-record round-trip for client_communication_portal",
    "one-record round-trip for audit",
    "one-record round-trip for dashboard"
  ],
  "data_sources": ["vendored Store blocks", "local sqlite"],
  "demo_data_requirements": ["one persisted record per capability"],
  "domain_acceptance_conditions": [
    "product boots",
    "own gates green",
    "one-record round-trip per capability",
    "envelope vocab open|in_progress|closed enforced by schema, not prose",
    "open×walk_in clinic_load_score is 0.45 not persist stub 1.0",
    "HotelOps H claimed_actor only; CORS allowlist refuses *"
  ],
  "domain_purpose": "A clinic-operations hub for veterinary practice operators. It centralizes patient charts, appointment slots, prescriptions, invoices, and client messages so a small clinic can run a pilot without a full PIMS.",
  "domain_rules": [
    "status vocabulary is schema-enforced: open, in_progress, closed",
    "reserved-keyword fields are refused",
    "client actor/user_id is claimed_actor only"
  ],
  "high_impact_actions": ["create", "update", "delete"],
  "mission": "A clinic-operations hub for veterinary practice operators.",
  "primary_users": ["clinic operators"],
  "prohibited_autonomous_actions": [
    "deploy",
    "store publish",
    "export when the pilot suite is red",
    "edit vendor/** or build_ledger.jsonl"
  ],
  "required_exports": ["pilot_candidate zip after PRODUCT+STORE green"],
  "required_product_modules": [
    "veterinary_care_core",
    "patient_records_management",
    "appointment_scheduling",
    "prescription_management",
    "billing_and_invoicing",
    "client_communication_portal",
    "audit",
    "dashboard"
  ],
  "required_roles": ["operator", "admin"],
  "security_regulatory_rules": [
    "offline platform — no network, no HTTP store callbacks",
    "fail-closed mutating auth; CORS allowlist only"
  ]
}

Done when (from intake blueprint):
- product boots
- own gates green
- one-record round-trip per capability
- envelope vocab open|in_progress|closed enforced by schema, not prose
- clinic_load_score computed (0.45 on schema sample)
- sealed paths untouched


==================================================
ACCEPTANCE (harness, not the coder)
==================================================

Fails loud. The run is not done until ALL of these are true.
- the product boots  [check:boot]
- own gates green  [check:gates]
- one-record round-trip per capability (POST creates, GET returns it)  [check:round_trip]
- every capability accepts a POST built from its own FIELDS/CONSTRAINTS  [check:writer_behaviour]
- every REUSE keep-path handler accepts a schema-sample POST without Unknown action  [check:reuse_accept]
- PRODUCT accept-payload: appointment_scheduling event_bus step_0, step_1, step_2+ prepared  [check:event_bus_workflow]
- envelope vocab open, in_progress, closed enforced by schema  [check:envelope_schema]
- PRODUCT gate: pytest -m pilot  [check:product_gate]
- STORE gate: scripts/acceptance.py ≥12 measured checks k/k  [check:store_gate]
- ledger records pilot_ready=true (harness-owned; WRITER must not edit build_ledger.jsonl)  [check:ledger]
- launching-ready full-pilot authorship: ≥5 keepable agent-written handlers (this roster: 8)  [check:full_pilot_authorship]
- PHASE 1 BACKEND accepted  [check:writer_phase_backend]
- PHASE 2 FRONTEND + RAG accepted  [check:writer_phase_frontend_rag]
- PHASE 3 INTEGRATION accepted  [check:writer_phase_integration]


==================================================
FORBIDDEN
==================================================

- thin SUCCESS (code-cycle green, pilot_ready=false)
- authorship below the launching-ready full-pilot floor (<5 handlers)
- decorative tests
- reserved-keyword fields (action inside the payload dict, id as a domain field)
- unlisted blocks; inventing a block id
- editing vendor/**, vendor_blocks/**, vendor_blocks_mirror/**, blocks.lock.json, build_ledger.jsonl, .git/**
- binding formula_executor when it is not vendored (PATHS_VIOLATED if you patch vendor to add it)
- persist to a table alembic 0001 did not create
- execute(block_id, payload) or action=None
- empty BLOCK_DEFAULT_ACTIONS on a REUSE handler that binds Store blocks
- forwarding the PRODUCT schema sample as an event_bus workflow step input
- unprepared step_0 / step_1 / step_2 on appointment_scheduling
- omitting workflow input['result']
- leftover airport/retail capability ids, UI titles, or acceptance CORE names
- open CORS (`*`) or treating client actor/user_id as authenticated identity
