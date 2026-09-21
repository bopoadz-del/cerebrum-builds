"""Handler for capability local_drive.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

The lead files and the project sheets live on disk before they are ingested,
so the platform needs a confined local file surface: the vendored
``local_drive`` block reads and writes under one root, and this handler
enforces the confinement before the block is ever called. A relative path
that climbs out of the configured root (``..``, an absolute path, a symlink
target, a null byte) is refused here -- the block's ``never`` scope lists
``file:escape_root`` and the refusal is what keeps that promise.

Scope
-----
READS  this capability's own columns from the caller's record; files under
       the configured root (``LOCAL_DRIVE_ROOT``, defaulting to
       ``STORAGE_PATH``); app.dispatch (the local offline block runtime);
       app.store (the ``local_drive`` table, through the route's
       tenant-scoped save).
WRITES app.dispatch.execute() results; a file under the configured root when
       the operation is a write; exactly one row in ``local_drive`` via the
       ROUTE's ``store.save(entity, record, tenant_id)`` -- this handler has
       no tenant and never persists directly.
NEVER  a path that escapes the configured root; absolute paths from a caller;
       unguarded network egress; ``vendor/**`` (sealed, read-only); another
       capability's table; ``tests/**``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "local_drive"
ENTITY = "local_drive"
BLOCK_IDS = ['local_drive']
#: The block takes its operation from the input, not from an action keyword;
#: ``LocalDriveBlock`` exposes none, so the action stays None on purpose and
#: the operations below are the block's own.
BLOCK_DEFAULT_ACTIONS: Dict[str, str] = {}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'root_path', 'relative_path', 'operation',
    'bytes_written', 'content_preview', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'relative_path': {'required': True},
    'operation': {'allowed_values': ['read', 'write', 'list', 'delete'],
                  'required': True},
}


def _text(data: Dict[str, Any], name: str, limit: int = 4000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def drive_root(data: Dict[str, Any]) -> Path:
    """The one root this capability may touch. Never a caller-chosen root.

    ``root_path`` is a record of what the caller believes the root is; it is
    never the value used. The root comes from ``LOCAL_DRIVE_ROOT`` (or the
    storage root) so a caller cannot widen the confinement by asking for "/" .
    """
    configured = str(
        os.environ.get("LOCAL_DRIVE_ROOT")
        or os.environ.get("STORAGE_PATH")
        or "./data"
    )
    return Path(configured).resolve()


def resolve_within_root(root: Path, relative: str) -> Path:
    """Resolve *relative* under *root*, refusing anything that escapes it."""
    raw = str(relative or "").strip()
    if not raw:
        raise InputRefused("relative_path is required")
    if "\x00" in raw:
        raise InputRefused("relative_path contains a null byte")
    if raw.startswith("/") or raw.startswith("\\") or (len(raw) > 1 and raw[1] == ":"):
        raise InputRefused("relative_path must be relative to the drive root")
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise InputRefused(
            f"relative_path escapes the drive root: {raw!r}"
        ) from exc
    return candidate


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "local-drive"
        relative = _text(data, "relative_path", 1000)
        operation = _text(data, "operation", 20).lower() or "read"
        content = _text(data, "content_preview", 20000)
        if operation not in EDGE_CONSTRAINTS['operation']['allowed_values']:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "operation must be one of: "
                         + ", ".join(EDGE_CONSTRAINTS['operation']['allowed_values']),
            }
        root = drive_root(data)
        root.mkdir(parents=True, exist_ok=True)
        target = resolve_within_root(root, relative)
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    result = runner(
        "local_drive",
        {
            "root_path": str(root),
        "root_path_requested": _text(data, "root_path", 500),
            "relative_path": str(target.relative_to(root)),
            "path": str(target),
            "operation": operation,
            "content": content,
        },
        action=None,
    )
    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    written = 0
    if operation == "write" and content:
        written = len(content.encode("utf-8"))
    files = result.get("files") if isinstance(result, dict) else None
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "root_path": str(root),
        "root_path_requested": _text(data, "root_path", 500),
        "relative_path": str(target.relative_to(root)),
        "operation": operation,
        "bytes_written": written,
        "exists": target.exists(),
        "listing_count": len(files) if isinstance(files, list) else None,
        "confined_to_root": True,
        "blocks": runner.report(),
    }
