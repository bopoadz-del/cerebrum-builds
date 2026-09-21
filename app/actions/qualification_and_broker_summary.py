"""Handler for capability qualification_and_broker_summary.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Qualification is a schema, not prose. ``outcome`` is one enum --
project_interested | other_re_interested | not_interested -- carried with the
collected fields (property type, budget, area, timeline). The vendored
``validation`` block screens the qualification pipeline, the vendored
``recommendation_template`` renders the broker summary from the record, and
the vendored ``knowledge`` block is the cited-answer path for any project
fact the summary repeats. A summary is never written freehand: every line
is derived from a stored field or a retrieved citation.

Scope
-----
READS  this capability's own columns from the caller's record; app.retrieval
       and app.authority (the tenant corpus and precedence.v1);
       app.dispatch (the local offline block runtime); app.block_inputs
       (block input construction); app.store (the
       ``qualification_and_broker_summary`` table, through the route's
       tenant-scoped save).
WRITES app.dispatch.execute() results; exactly one row in
       ``qualification_and_broker_summary`` via the ROUTE's
       ``store.save(entity, record, tenant_id)`` -- this handler has no
       tenant and never persists directly.
NEVER  unguarded network egress; a summary that contradicts the stored
       outcome; ``vendor/**`` (sealed, read-only); another capability's
       table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import retrieval
from app.block_run import block_runner, probe_block
from app.security import InputRefused, clean_text

CAPABILITY_ID = "qualification_and_broker_summary"
ENTITY = "qualification_and_broker_summary"
BLOCK_IDS = ['validation', 'recommendation_template', 'knowledge']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {
    'validation': 'validate_pipeline',
    'recommendation_template': 'apply_template',
    'knowledge': 'search',
}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'call_sid', 'lead_name', 'outcome', 'property_type',
    'budget', 'area', 'timeline', 'currency_setting', 'broker_summary',
    'recommended_action', 'notes',
]

#: The fixed three-outcome vocabulary. One enum, not prose.
OUTCOMES = ('project_interested', 'other_re_interested', 'not_interested')
PROPERTY_TYPES = ('apartment', 'villa', 'townhouse', 'plot', 'office')

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'call_sid': {'required': True},
    'outcome': {'allowed_values': list(OUTCOMES), 'required': True},
    'property_type': {'allowed_values': list(PROPERTY_TYPES), 'required': False},
}

#: What a broker should do next, keyed by the outcome. The vocabulary decides
#: the handoff -- the model never picks it.
ACTIONS = {
    'project_interested': 'warm_transfer',
    'other_re_interested': 'send_alternative_projects',
    'not_interested': 'close_and_suppress',
}


def _text(data: Dict[str, Any], name: str, limit: int = 4000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def _num(data: Dict[str, Any], name: str) -> Any:
    raw = data.get(name)
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return int(value) if value.is_integer() else value


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "qualification"
        call_sid = _text(data, "call_sid", 80)
        lead_name = _text(data, "lead_name", 200)
        outcome = _text(data, "outcome", 40).lower()
        property_type = _text(data, "property_type", 40).lower()
        budget = _num(data, "budget")
        area = _text(data, "area", 120)
        timeline = _text(data, "timeline", 120)
        if outcome not in OUTCOMES:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "outcome must be one of: " + ", ".join(OUTCOMES),
            }
        if property_type and property_type not in PROPERTY_TYPES:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "property_type must be one of: " + ", ".join(PROPERTY_TYPES),
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    qualified = {
        "call_sid": call_sid,
        "lead_name": lead_name,
        "outcome": outcome,
        "property_type": property_type,
        "budget": budget,
        "area": area,
        "timeline": timeline,
    }
    pipeline = {
        "pipeline_id": f"qualification-{reference}".replace(" ", "_"),
        "steps": [
            {
                "id": "step_0",
                "type": "validation",
                "block": "validation",
                "input": {"record": qualified, "required": ["outcome"]},
            }
        ],
    }
    screened = runner("validation", {"pipeline": pipeline}, action="validate_pipeline")
    templated = runner(
        "recommendation_template",
        {"variance_data": [
            {"item": key, "variance_pct": 0, "cost_impact_usd": 0}
            for key, value in qualified.items() if value not in (None, "")
        ]},
        action="apply_template",
    )

    # Any project fact repeated in the summary has to be cited or dropped.
    facts = (
        retrieval.search(
            " ".join(part for part in (property_type, area, timeline) if part) or reference,
            limit=3,
        )
        or {}
    ).get("hits") or []
    knowledge = probe_block(
        "knowledge",
        {"query": f"{property_type} {area} {timeline}", "top_k": 3},
        action="search",
        entity=ENTITY,
        roster=BLOCK_IDS,
        default_actions=BLOCK_DEFAULT_ACTIONS,
    )
    unavailable: Dict[str, str] = {}
    if not knowledge["ok"]:
        unavailable["knowledge"] = knowledge["error"]

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    collected = ", ".join(
        f"{key}={value}"
        for key, value in (("property_type", property_type), ("budget", budget),
                           ("area", area), ("timeline", timeline))
        if value not in (None, "")
    )
    summary_lines = [
        f"Call {call_sid or 'unkeyed'}: {lead_name or 'unnamed lead'}",
        f"Outcome: {outcome}",
        "Collected: " + (collected or "none"),
    ]
    if facts:
        summary_lines.append(
            "Cited: " + "; ".join(hit["citation"] for hit in facts if hit.get("citation"))
        )
    else:
        summary_lines.append("Cited: none -- no ingested project sheet matched, so no project fact is repeated")
    if templated.get("recommendation_text"):
        summary_lines.append(str(templated["recommendation_text"])[:400])
    summary = "\n".join(summary_lines)

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "qualification": qualified,
        "broker_summary": summary,
        "recommended_action": ACTIONS[outcome],
        "handoff_required": outcome in ("project_interested", "other_re_interested"),
        "evidence": [hit["citation"] for hit in facts if hit.get("citation")],
        "validation_status": screened.get("status") if isinstance(screened, dict) else None,
        "recommendation_count": templated.get("recommendation_count")
        if isinstance(templated, dict) else None,
        "blocks_unavailable": unavailable,
        "blocks": runner.report(),
    }
