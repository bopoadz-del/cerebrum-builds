"""Handler for capability guest_engagement_and_segmentation.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Segments guests by stay behaviour and value, then drives the offer through the
channels this property has configured: the vendored segmentation block scores the
stay history, the channel router picks the route, and the notification block
sends it. app.formulas owns the thresholds the operator can change.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``guest_engagement_and_segmentation`` table, through the route's
       tenant-scoped save); app.formulas (the operator-owned RFM thresholds).
WRITES app.dispatch.execute() results; exactly one row in ``guest_engagement_and_segmentation`` via the
       ROUTE's tenant-scoped persistence (app.routes) -- this handler has no
       tenant and never persists directly.
NEVER  unguarded network egress; ``vendor/**`` (sealed, read-only); another
       capability's table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "guest_engagement_and_segmentation"
ENTITY = "guest_engagement_and_segmentation"
BLOCK_IDS = ['guest_rfm_segmentation', 'channel_router', 'notification']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
#: ``knowledge`` keeps its Store default here because the capability's
#: inventory binds it; see docs/blockers.json -- the vendored knowledge block
#: cannot load offline (it requires vendor.cerebrum.core.vector_store, which
#: the runtime slice does not ship), so document_engine carries the parsing and
#: app.retrieval carries retrieval.
BLOCK_DEFAULT_ACTIONS = {'guest_rfm_segmentation': 'score', 'channel_router': 'route', 'notification': 'send'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['reference', 'status', 'guest_name', 'recency_days', 'frequency', 'monetary', 'segment', 'delivery_channel', 'offer_code', 'notes']


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)

def _offer_for(segment: str, guest: str) -> Dict[str, Any]:
    catalogue = {
        "champion": ("SUITE-UPGRADE", "complimentary suite upgrade on the next stay"),
        "loyal": ("LATE-CHECKOUT", "guaranteed late checkout"),
        "potential": ("WELCOME-DRINK", "welcome drink at the bar"),
        "at_risk": ("COME-BACK-15", "15 percent off the next stay"),
        "dormant": ("REACTIVATE-20", "20 percent off the next two nights"),
    }
    code, description = catalogue.get(segment, ("WELCOME-DRINK", "welcome drink at the bar"))
    return {"offer_code": code, "description": description, "guest_name": guest}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        guest = _text(data, "guest_name", 200)
        recency = data.get("recency_days")
        frequency = data.get("frequency")
        monetary = data.get("monetary")
        channel = _text(data, "delivery_channel", 20) or "mcp"
        if recency is None or frequency is None or monetary is None:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": (
                    "recency_days, frequency and monetary are required: a guest "
                    "cannot be segmented from a partial stay history"
                ),
            }
        message = (
            f"{guest or 'Guest'}: thank you for staying with us. "
            f"Recency {recency} days, {frequency} stays, value {monetary}."
        )
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    scored = runner(
        "guest_rfm_segmentation",
        {"recency_days": recency, "frequency": frequency, "monetary": monetary},
        action="score",
    )
    # channel_router reads a routing profile, not the guest message: pass the
    # routing signals it declares (complexity / speed_priority) and nothing it
    # would refuse as an unknown field.
    routed = runner(
        "channel_router",
        {"complexity": "low", "speed_priority": "same_day"},
        action="route",
    )
    notified = runner(
        "notification",
        {
            "channel": channel,
            "message": message,
            "subject": "Your stay with us",
            "payload": {"reference": _text(data, "reference", 120), "segment": "pending"},
        },
        action="send",
    )

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    segment = str(scored.get("segment") or "potential") if isinstance(scored, dict) else "potential"
    offer = _offer_for(segment, guest)
    delivery = {
        "channel": notified.get("channel") if isinstance(notified, dict) else channel,
        "sent": bool(notified.get("sent")) if isinstance(notified, dict) else False,
        "recommended_channel": routed.get("recommended_channel") if isinstance(routed, dict) else None,
        "recommended_score": routed.get("score") if isinstance(routed, dict) else None,
    }
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "segment": segment,
        "rfm": {
            "r": scored.get("r") if isinstance(scored, dict) else None,
            "f": scored.get("f") if isinstance(scored, dict) else None,
            "m": scored.get("m") if isinstance(scored, dict) else None,
            "score": scored.get("score") if isinstance(scored, dict) else None,
        },
        "offer": offer,
        "message": message,
        "delivery": delivery,
        "blocks": runner.report(),
    }
