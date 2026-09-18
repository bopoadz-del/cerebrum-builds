# Named blockers

Two vendored Store slices in this checkout cannot load. They are **not**
patched (`vendor/**` is sealed and read-only for the WRITER seat) and **not**
bound by any capability: binding a block that cannot import would make the
capability report a failure it cannot fix, and stubbing the call would be a
lie. Both are recorded in `docs/blockers.json`, probed live by
`app/vendor_health.py` on `GET /v1/vendor_health`, and asserted by
`tests/test_vendor_health.py`.

## `notification` — does not parse

```
$ python -m py_compile vendor/cerebrum/blocks/notification.py
Sorry: IndentationError: expected an indented block after 'try' statement
on line 230 (notification.py, line 231)
```

The module cannot be imported, so `vendor/blocks/notification/block.py`
cannot resolve its Store class and `execute("notification", ...)` answers an
error envelope. **Fallback used instead:** `checkin_notifications` publishes
the prepared MCP event on the `event_bus` slice (topic, payload dict, message,
`channel=mcp`, `tool=event_bus`) and enqueues a durable `queue` job; the
check-in row itself is the audit trail of the alert.

**Owner action:** ship a parseable `vendor/cerebrum/blocks/notification.py`.

## `knowledge` — missing core module

```
$ python -c "import vendor.cerebrum.blocks.knowledge"
ImportError: cannot import name 'vector_store' from 'vendor.cerebrum.core'
```

The vendored core slice ships no `vector_store`, so the RAG knowledge block
raises at import time. **Fallback used instead:** `guest_notes_and_preferences`
persists through the `database` slice and caches in the `memory` slice, and
tenant retrieval runs through `app/retrieval.py` (lexical, in-process, no
network), exposed over HTTP at `POST /v1/corpus/documents`,
`POST /v1/rag/ingest` and `POST|GET /v1/rag/query` (steward twins at
`/v1/steward/rag/*`). Ingest writes one `corpus_documents` row for the
resolved tenant; query ranks that tenant's rows only.

**Owner action:** ship `vendor/cerebrum/core/vector_store.py` in the vendored
core slice.

## Bound blocks — all verified loadable

```
capture, validation, database, dashboard, analytics, formula_executor,
memory, event_bus, queue, audit
```

`tests/test_vendor_health.py::test_every_bound_block_is_available` fails if any
bound block stops loading.

## Not runtime defects: what this tree still does not carry

Recorded here rather than left for a reader to discover, because both are
visible to anyone who runs `app.factory.build.level_grade.grade_workspace`
on this checkout:

* **The 14-class contract surfaces are incomplete.** `app/agents/manifests`,
  `app/workflows`, `app/connectors`, `product-dna`, `docs/provenance` and
  `docs/certification` are absent. Nothing the platform serves depends on
  them — the suite, the RAG corpus, the routes, the acceptance script and
  the release gate all pass without them — but they are part of the
  factory's founding-customer file contract, so the level grade reports
  them as a blocker on `FOUNDING_CUSTOMER_READY` and stops at
  `STORE_GREEN`.
* **Authorship is template-majority.** `docs/build_provenance.json` records
  112 artifacts: 42 produced by the coding agent and 70 emitted by the
  factory's deterministic templates. The launching-ready floor is met
  (7 agent-written capability handlers, `cli_authored_ids` = 7, need ≥ 5),
  so the pilot is exportable; the template majority is the second blocker
  on `FOUNDING_CUSTOMER_READY`. It is not corrected by relabelling — the
  file records who produced each artifact.
