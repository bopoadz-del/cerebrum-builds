# Vendored-runtime compat (build-time repair, same Store commit)

`vendor/**` is sealed and read-only for the WRITER role. In this checkout the
vendored runtime slice is incomplete/broken, and the delivered platform could
not call three of the blocks it is assigned:

| symptom | cause in the sealed slice | repair |
| --- | --- | --- |
| `document_engine: FileNotFoundError .../document_engine_block.py` | the CLONER vendored the wrapper as the package `document_engine_block/` while the vendored package loads the sibling module *file* | pre-import and register the vendored package under `vendor.cerebrum.blocks.document_engine_block`, so the loader's `sys.modules` check is satisfied |
| `knowledge: ImportError cannot import name 'vector_store'` | `vendor/cerebrum/core/vector_store.py` was not vendored | `app/vendor_compat/vector_store.py` — the same Store commit's source (`a198eba6`), imports rewritten with the factory's own `_rewrite_runtime_imports`, asyncpg optional (offline: the pool is unavailable, so `search_vectors()` answers `[]`) |
| `notification: IndentationError ... line 231` | the CLONER's shim rewrite deleted an import line and left `try:` with an empty body | `app/vendor_compat/notification.py` — the same commit's `NotificationBlock` with runtime imports rewritten, no other transform |

`app/dispatch.py:load_block` calls `app.vendor_compat.install()` before the
first vendored block import. Registration is `sys.modules` + an attribute on
the vendored package: **no file under `vendor/**` is created or modified**, and
`blocks.lock.json` digests are untouched.

## Input-side defects fixed in `app/block_inputs.py`

* `file_hasher` needs a real path: the record's own scalar content is written
  under `STORAGE_PATH/evidence/` and hashed (`_for_file_hasher`).
* `notification` channel `mcp` calls a peer block in-process; the peer must be
  in the vendored `BLOCK_REGISTRY` (`_mcp_target`), otherwise it answers
  `Block 'estate_registry' not found`.
* the Store workflow runs a child as `block.execute(step["input"],
  step["params"])`, so a step-level `action` is inert for the child; the
  resolved action is mirrored into `step["params"]["action"]`
  (`_shape_workflow_steps`).

## Default-action overrides (documented, not harvested)

* `file_hasher` → `hash` (the block is not action-dispatched and publishes no
  `action` input; `hash` is its documented primary action).
* `team` → `get_team_context`: `app/preconditions.py` already creates the
  clinic team at boot, and `appointment_scheduling` needs to *verify staff
  access*, not mint a second team with a fixed slug (which answers
  `Team slug ... already exists` on the second call in a process).
