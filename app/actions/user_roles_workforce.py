"""Capability user_roles_workforce — users, roles, shop assignment, shifts.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``team``     — creates the workforce team for the shop (one user per shop,
    plus the central managers and the drivers), keyed uniquely per record;
  * ``database`` — records the membership row;
  * ``workflow`` — the onboarding run. EVERY child is prepared in source:
      - step_0 ``database``  — writes the membership row;
      - step_1 ``audit``     — records the role grant;
      - step_2 ``event_bus`` — publishes the workforce change with the full
        contract (topic, payload dict, message, channel=mcp, action=publish);
  * ``audit``    — appends the immutable role/shift assignment entry.

Scope
-----
READS  the caller's payload.
WRITES nothing (dispatch results are returned; the route persists).
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from app.block_inputs import prepare_block_input
from app.dispatch import execute

CAPABILITY_ID = "user_roles_workforce"
ENTITY = "user_roles_workforce"
BLOCK_IDS = ["team", "database", "workflow", "audit"]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "team": "create_team",
    "database": "insert",
    "workflow": "run",
    "audit": "log",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "user_name",
    "user_email",
    "role",
    "shop_code",
    "shift",
    "notes",
    "status",
]


def _member_context(record: Dict[str, Any]) -> Dict[str, Any]:
    """Who is being placed, in which shop, as which role and shift."""
    reference = str(record.get("reference") or "sample")
    shop = str(record.get("shop_code") or "chain")
    return {
        "reference": reference,
        "user_id": "user:%s" % reference,
        "name": str(record.get("user_name") or reference),
        "email": str(record.get("user_email") or ""),
        "role": str(record.get("role") or "operator"),
        "shop": shop,
        "shift": str(record.get("shift") or "morning"),
        # Unique per record so a re-POST never collides on the team slug.
        "slug": ("%s-%s-%s" % (reference, shop, uuid.uuid4().hex[:8]))
        .lower()
        .replace(" ", "-"),
    }


def _onboarding_steps(
    record: Dict[str, Any], member: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Prepared workflow children: membership write, then the role grant."""
    values = prepare_block_input("database", record, entity=ENTITY)["values"]
    audit_input = prepare_block_input("audit", record, entity=ENTITY)
    audit_input["event_action"] = "role_assigned"
    audit_input["details"] = {
        "user_id": member["user_id"],
        "role": member["role"],
        "shop_code": member["shop"],
        "shift": member["shift"],
    }
    return [
        {
            "id": "step_0",
            "block": "database",
            "action": "insert",
            "input": {"table": ENTITY, "values": values},
            "params": {"action": "insert"},
        },
        {
            "id": "step_1",
            "block": "audit",
            "action": "log",
            "input": audit_input,
            "params": {"action": "log"},
        },
        {
            "id": "step_2",
            "block": "event_bus",
            "action": "publish",
            "input": {
                "topic": "workforce.role_assigned",
                "payload": {
                    "reference": member["reference"],
                    "user_id": member["user_id"],
                    "role": member["role"],
                    "shop_code": member["shop"],
                    "shift": member["shift"],
                },
                "message": "%s placed as %s at %s on the %s shift"
                % (member["name"], member["role"], member["shop"], member["shift"]),
                "channel": "mcp",
                "tool": "event_bus",
            },
            "params": {"action": "publish"},
        },
    ]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    member = _member_context(data)
    steps = _onboarding_steps(data, member)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(
            block_id, data, entity=ENTITY, steps=steps if block_id == "workflow" else None
        )
        if block_id == "team":
            prepared["user_id"] = member["user_id"]
            prepared["name"] = member["name"]
            prepared["slug"] = member["slug"]
            prepared["plan"] = "free"
        if block_id == "audit":
            prepared["event_action"] = "membership_recorded"
            prepared["details"] = {
                "user_id": member["user_id"],
                "role": member["role"],
                "shop_code": member["shop"],
                "shift": member["shift"],
            }
        result = execute(
            block_id, prepared, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
        )
        results[block_id] = result
        if isinstance(result, dict) and (
            result.get("status") in ("error", "failed", "partial")
            or result.get("ok") is False
            or "error" in result
        ):
            errors[block_id] = str(result.get("error") or result)[:200]
    if errors:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
            "results": results,
        }
    return {"ok": True, "capability": CAPABILITY_ID, "results": results}
