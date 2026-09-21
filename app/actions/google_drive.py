"""Handler for capability google_drive.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

STUBBED CONNECTOR, DECLARED AS SUCH. No Google credentials were supplied, so
the vendored ``google_drive`` block answers "Not authenticated" and this
capability records that state by name -- ``drive_mode`` stays ``stubbed`` and
``blocks_unavailable`` names the block -- instead of pretending a folder was
listed. The credentials are deploy-time settings read from the environment,
never payload fields this capability requires: when ``GOOGLE_REFRESH_TOKEN`` /
``GOOGLE_CLIENT_ID`` /
``GOOGLE_CLIENT_SECRET`` (or ``GOOGLE_ACCESS_TOKEN``) are set, the same code
path performs the real call; nothing else changes.

Project sheets arrive as uploads either way, so the ingest path does not
depend on this connector: a sheet dropped in local_drive is ingested by
app.rag_routes through the same retrieval pipeline.

Scope
-----
READS  this capability's own columns from the caller's record; the Google
       settings from the process environment (never a literal); app.dispatch
       (the local offline block runtime); app.store (the ``google_drive``
       table, through the route's tenant-scoped save).
WRITES app.dispatch.execute() results; exactly one row in ``google_drive``
       via the ROUTE's ``store.save(entity, record, tenant_id)`` -- this
       handler has no tenant and never persists directly.
NEVER  claiming a live Drive connection without credentials; unguarded
       network egress; ``vendor/**`` (sealed, read-only); another
       capability's table; ``tests/**``.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from app.block_run import block_runner, probe_block
from app.security import InputRefused, clean_text

CAPABILITY_ID = "google_drive"
ENTITY = "google_drive"
BLOCK_IDS = ['google_drive']
#: The block does not dispatch on an action keyword; the operation travels in
#: the input. The action stays empty on purpose.
BLOCK_DEFAULT_ACTIONS: Dict[str, str] = {}
#: This capability's own domain columns. The three credential settings are
#: declared by the compiled spec (the connector names them), so they travel
#: with the record; they are credential material and are never logged.
CAPABILITY_FIELDS = [
    'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REFRESH_TOKEN',
    'reference', 'status', 'drive_mode', 'folder_id', 'file_name',
    'operation', 'credential_setting', 'notes',
]

EDGE_CONSTRAINTS = {
    # Deploy-time settings, not caller fields: the connector reads them from
    # the environment, so this capability never requires them in a payload
    # (requiring them made the route refuse its own schema sample).
    'GOOGLE_CLIENT_ID': {'required': False},
    'GOOGLE_CLIENT_SECRET': {'required': False},
    'GOOGLE_REFRESH_TOKEN': {'required': False},
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'drive_mode': {'allowed_values': ['stubbed', 'live'], 'required': True},
    'operation': {'allowed_values': ['upload', 'download', 'list'], 'required': True},
    'file_name': {'required': False, 'format': 'unset'},
}

#: The settings that turn the live connector on, named so the operator knows
#: exactly what to set. No defaults.
CREDENTIAL_SETTINGS = (
    "GOOGLE_REFRESH_TOKEN",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
)


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def configured() -> bool:
    if str(os.environ.get("GOOGLE_ACCESS_TOKEN") or "").strip():
        return True
    return all(str(os.environ.get(key) or "").strip() for key in CREDENTIAL_SETTINGS)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "google-drive"
        folder_id = _text(data, "folder_id", 200) or "root"
        file_name = _text(data, "file_name", 300)
        operation = _text(data, "operation", 20).lower() or "list"
        if operation not in EDGE_CONSTRAINTS['operation']['allowed_values']:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "operation must be one of: "
                         + ", ".join(EDGE_CONSTRAINTS['operation']['allowed_values']),
            }
        # Credential material travels with the record but is never echoed
        # back and never logged: only which of the settings came with the
        # call is reported, by name.
        supplied_with_record = [
            key for key in CREDENTIAL_SETTINGS
            if isinstance(data.get(key), str) and data.get(key).strip()
        ]
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    live = configured()
    probed = probe_block(
        "google_drive",
        {"folder_id": folder_id, "file_name": file_name, "operation": operation},
        action=None,
        entity=ENTITY,
        roster=BLOCK_IDS,
        default_actions=BLOCK_DEFAULT_ACTIONS,
    )
    unavailable: Dict[str, str] = {}
    if not probed["ok"]:
        unavailable["google_drive"] = probed["error"]

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "drive_mode": "live" if (live and probed["ok"]) else "stubbed",
        "folder_id": folder_id,
        "file_name": file_name,
        "operation": operation,
        "credentials_configured": live,
        "credentials_supplied_with_record": supplied_with_record,
        "credential_setting": ", ".join(CREDENTIAL_SETTINGS),
        "files": (probed["result"].get("files") if probed["ok"] else None),
        "blocks_unavailable": unavailable,
        "blocker": "" if probed["ok"] else (
            "google_drive connector is stubbed: set "
            + ", ".join(CREDENTIAL_SETTINGS)
            + " (or GOOGLE_ACCESS_TOKEN) to activate it"
        ),
        "blocks": runner.report() or [
            {"block": "google_drive", "action": None, "ok": probed["ok"],
             "error": probed["error"]}
        ],
    }
