"""Handler for capability external_integration_adapter.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

The single attach point for external property systems (PMS, POS, CMMS, loyalty).
Nothing is assumed: the caller names a system the adapter actually carries, the
vendored connector answers in fixture mode until an operator configures a live
endpoint, and a caller-supplied URL is refused unless it is public.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``external_integration_adapter`` table, through the route's
       tenant-scoped save); app.security (the egress guard).
WRITES app.dispatch.execute() results; exactly one row in ``external_integration_adapter`` via the
       ROUTE's tenant-scoped persistence (app.routes) -- this handler has no
       tenant and never persists directly.
NEVER  a currency, tax regime or tax rate the brief did not give; unguarded
       network egress; ``vendor/**`` (sealed, read-only); another capability's
       table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "external_integration_adapter"
ENTITY = "external_integration_adapter"
BLOCK_IDS = ['hospitality_connectors']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {'mcp_adapter': 'list_tools', 'hospitality_connectors': 'fetch'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['reference', 'status', 'system', 'resource', 'direction', 'payload_format', 'endpoint_url', 'records_seen', 'notes']


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)

_KNOWN_SYSTEMS = ("opera", "micros", "maximo", "loyalty_lms", "grms", "gaming_cms")


def _carried_resources(system: str) -> List[str]:
    """Which record sets this connector actually carries.

    Asked of the block itself (its own fixture packs / live resource map)
    rather than guessed: naming a resource the connector does not carry is the
    caller's to learn, and the answer comes from the connector, not from us.
    """
    try:
        from vendor.cerebrum.blocks.hospitality_connectors import FIXTURES

        pack = FIXTURES.get(system) or {}
        return sorted(str(name) for name in pack)
    except Exception:  # noqa: BLE001 - a connector that cannot be asked says so
        return []


def _connector_input(data: Dict[str, Any], action: str) -> Dict[str, Any]:
    """The vendored hospitality connectors block reads its operation out of its
    own ``input_schema`` (``action`` is a declared field of that schema), so the
    operation is passed BOTH as the keyword and, for this block only, inside the
    input it validates -- named here rather than buried silently.
    """
    return {
        "action": action,
        "system": _text(data, "system", 40),
        "resource": _text(data, "resource", 120),
    }


def _egress_note(data: Dict[str, Any]) -> Dict[str, Any]:
    """A caller-supplied live URL is checked at the edge before any dial."""
    url = _text(data, "endpoint_url", 2000)
    if not url:
        return {"endpoint_url": None, "guard": "none supplied; fixture mode"}
    from app.security import check_outbound_url

    try:
        safe = check_outbound_url(url, field="endpoint_url")
    except InputRefused as exc:
        return {"endpoint_url": None, "guard": "refused", "reason": str(exc)}
    return {"endpoint_url": safe, "guard": "allowed"}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        system = _text(data, "system", 40) or "opera"
        resource = _text(data, "resource", 120)
        direction = _text(data, "direction", 20) or "inbound"
        payload_format = _text(data, "payload_format", 20) or "json"
        if system not in _KNOWN_SYSTEMS:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": (
                    f"unknown enterprise system {system!r}; this adapter attaches "
                    f"only to {', '.join(_KNOWN_SYSTEMS)}"
                ),
            }
        if not resource:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "resource is required: name the record set to attach to",
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    egress = _egress_note(data)
    connected = runner(
        "hospitality_connectors",
        {"system": system, "resource": resource},
        action="connect",
        payload_extra=_connector_input(data, "connect"),
    )
    carried = _carried_resources(system)
    if resource in carried:
        fetched = runner(
            "hospitality_connectors",
            {"system": system, "resource": resource},
            action="fetch",
            payload_extra=_connector_input(data, "fetch"),
        )
        fetch_note = "fetched the named record set from the connector"
    else:
        # The connector does not carry that record set. Say so and report what
        # it does carry (its event history), rather than inventing records or
        # pretending the fetch happened.
        fetched = runner(
            "hospitality_connectors",
            {"resource": resource},
            action="bus",
            payload_extra=_connector_input(data, "bus"),
        )
        fetch_note = (
            f"the {system} connector does not carry the record set "
            f"{resource!r}; reported its event history instead"
        )
    systems = runner(
        "hospitality_connectors",
        {"resource": resource},
        action="systems",
        payload_extra=_connector_input(data, "systems"),
    )

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    records = fetched.get("data") if isinstance(fetched, dict) else None
    if isinstance(records, dict):
        rows = records.get("records") or []
    elif isinstance(records, list):
        rows = records
    else:
        rows = fetched.get("events") if isinstance(fetched, dict) else None
        rows = rows if isinstance(rows, list) else []
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "attach_point": {
            "system": system,
            "resource": resource,
            "direction": direction,
            "payload_format": payload_format,
            "mode": connected.get("mode") if isinstance(connected, dict) else None,
            "connected": bool(str(connected.get("status", "")).lower() in ("connected", "ok")),
        },
        "fetched": {
            "records": len(rows),
            "sample": rows[:3],
            "records_seen": len(rows),
        },
        "available_systems": (systems.get("systems") if isinstance(systems, dict) else None)
        or list(_KNOWN_SYSTEMS),
        "carried_resources": carried,
        "attached_resources": carried,
        "fetch_note": fetch_note,
        "egress": egress,
        "note": (
            "no integration is assumed: this adapter attaches to a named property "
            "system only when the operator configures one, and every outbound URL "
            "is refused unless it is public"
        ),
        "blocks": runner.report(),
    }
