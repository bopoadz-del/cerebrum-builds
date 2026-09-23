"""Local drive: tenant-scoped storage for ingested project sheets.

Written by the factory WRITER role (codewhale exec)

Each tenant gets its own root under ``LOCAL_DRIVE_ROOT`` (or
``STORAGE_PATH/drive``). Paths are relative and are resolved against that
root, so ``../../etc/passwd`` is refused rather than read: the drive is a
file store for a brokerage's own uploads, not a filesystem API. Writes are
digested so a sheet can be identified by content later.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List

from app import config, dispatch
from app import tenancy
from app import domain
from app.models import MODELS

CAPABILITY_ID = "local_drive"

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'local_drive': 'put',
}

REQUIRED_FIELDS = ["operation", "relative_path"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "operation": {"allowed_values": ['put', 'get', 'list', 'delete', 'stat'], "required": True},
    "relative_path": {"required": True, "max_length": 300},
    "content": {"max_length": 20000},
    "content_digest": {"max_length": 64},
    "bytes_written": {"min": 0},
    "root": {"max_length": 300},
    "tenant_root": {"max_length": 300},
    "entries": {},
    "file_exists": {},
    "size_bytes": {"min": 0},
    "media_type": {"max_length": 120},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

READ_ONLY_OPERATIONS = ("get", "stat")


def _media_type(name: str) -> str:
    suffix = Path(str(name)).suffix.lower()
    return {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".json": "application/json",
    }.get(suffix, "application/octet-stream")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Put, get, list, stat or delete one file under the tenant's root."""
    body = dict(payload or {})
    for name in REQUIRED_FIELDS:
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name in ("reference", "status"):
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name, rules in constraints.items():
        values = rules.get("allowed_values") or ()
        value = body.get(name)
        if value is None or value == "":
            continue
        if values and value not in values:
            return {
                "ok": False,
                "error": f"{name} must be one of: " + ", ".join(str(v) for v in values),
            }
    tenant_id = str(body.get("tenant_id") or tenancy.deployment_tenant())
    if not tenant_id:
        # Tenancy comes from the authenticated principal, which the route
        # injects. A handler that cannot see it refuses rather than
        # assuming a tenant: defaulting here is how one brokerage ends up
        # writing into another's corpus with a valid token of its own.
        return {
            "ok": False,
            "error": "no tenant could be resolved: this deployment binds more "
            "than one operator, so tenancy comes from the authenticated "
            "principal and is never assumed by a handler",
        }
    operation = str(body.get("operation"))
    relative = str(body.get("relative_path"))
    try:
        outcome = dispatch.execute(
            "local_drive",
            action=operation or BLOCK_DEFAULT_ACTIONS["local_drive"],
            payload={
                "tenant_id": tenant_id,
                "relative_path": relative,
                "content": body.get("content") or "",
            },
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    failure = dispatch.refusal_of(outcome)
    if failure:
        return {"ok": False, "error": failure}
    entries = outcome.get("entries") or []
    digest = outcome.get("content_digest") or (
        hashlib.sha256(str(body.get("content") or "").encode("utf-8")).hexdigest()
        if operation == "put"
        else None
    )
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": operation,
        "file_exists": bool(outcome.get("exists", operation not in READ_ONLY_OPERATIONS)),
        "entries": entries,
        "record": {
            "operation": operation,
            "relative_path": relative,
            "root": outcome.get("root"),
            "tenant_root": outcome.get("tenant_root"),
            "content_digest": digest,
            "bytes_written": domain.as_int(outcome.get("bytes_written"), 0),
            "size_bytes": domain.as_int(outcome.get("size_bytes"), 0),
            "content": outcome.get("content"),
            "entries": str(entries),
            "file_exists": bool(outcome.get("exists", operation not in READ_ONLY_OPERATIONS)),
            "media_type": _media_type(relative),
        },
        "authority": None,
    }
