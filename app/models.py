"""Entity contracts for CallOps: one model per capability.

``MODELS`` maps every capability id to its model class. An entity's name IS
its capability id — the same string is the handler module stem, the alembic
table name and the key ``app/store.py`` is called with.

Each class carries ``FIELDS`` (declared columns, in contract order),
``CONSTRAINTS`` (type, required, vocabulary, bounds) and
``from_dict``/``to_dict``. The route layer validates against exactly these
constraints, so a partial record is refused with 422 rather than completed
by the server, and a value outside a vocabulary is refused rather than
stored as free text.

Two columns are the platform envelope and appear on every entity:
``reference`` (the operator's own handle for the row) and ``status``
(open | in_progress | closed). Domain state lives in its own column —
``queue_state``, ``call_status``, ``delivery`` — so the envelope stays
honest about what it means.

Money columns are unset by design: the brief does not state a country, a
currency or a tax rate, so no default is invented here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ENVELOPE_STATUS_VALUES: Tuple[str, ...] = ("open", "in_progress", "closed")

#: Declared field type -> the annotation the model class carries. PEP 563
#: style (the annotation is a string), so ``Model.__annotations__`` states the
#: same type ``CONSTRAINTS`` enforces. Callers that build an instance from the
#: spec alone -- the acceptance harness samples one value per declared field --
#: read this rather than guessing "str" for a column declared ``int`` or
#: ``bool`` and then being refused by the platform's own validation.
PYTHON_TYPES: Dict[str, str] = {
    "int": "int",
    "float": "float",
    "bool": "bool",
    "datetime": "datetime",
    "date": "date",
    "time": "time",
    "str": "str",
}

PROPERTY_TYPES: Tuple[str, ...] = (
    "apartment",
    "villa",
    "townhouse",
    "plot",
    "office",
    "retail",
    "other",
)

TIMELINES: Tuple[str, ...] = (
    "immediate",
    "three_months",
    "six_months",
    "twelve_months",
    "browsing",
    "unknown",
)

CALL_STATES: Tuple[str, ...] = (
    "queued",
    "dialing",
    "answered",
    "pitched",
    "qualified",
    "transferred",
    "callback",
    "closed",
)

OUTCOMES: Tuple[str, ...] = (
    "project_interested",
    "other_re_interested",
    "not_interested",
    "none",
)

TWILIO_CALL_STATUSES: Tuple[str, ...] = (
    "initiated",
    "ringing",
    "answered",
    "completed",
    "failed",
    "busy",
    "no-answer",
)

LANGUAGES: Tuple[str, ...] = ("en", "ar")


def _field(
    name: str,
    type: str = "str",
    *,
    required: bool = False,
    allowed_values: Optional[Sequence[Any]] = None,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
    minimum_length: Optional[int] = None,
    maximum_length: Optional[int] = None,
    format: Optional[str] = None,
    note: str = "",
) -> Dict[str, Any]:
    spec: Dict[str, Any] = {"name": name, "type": type}
    if required:
        spec["required"] = True
    if allowed_values:
        spec["allowed_values"] = list(allowed_values)
    if minimum is not None:
        spec["min"] = minimum
    if maximum is not None:
        spec["max"] = maximum
    if minimum_length is not None:
        spec["min_length"] = minimum_length
    if maximum_length is not None:
        spec["max_length"] = maximum_length
    if format:
        spec["format"] = format
    if note:
        spec["note"] = note
    return spec


def _envelope() -> List[Dict[str, Any]]:
    return [
        _field("reference", required=True, note="the operator's handle for this row"),
        _field("status", required=True, allowed_values=ENVELOPE_STATUS_VALUES),
    ]


class Model:
    """Base for every entity. Subclasses are built by :func:`build_model`."""

    CAPABILITY_ID: str = ""
    TITLE: str = ""
    ENTITY: str = ""
    DESCRIPTION: str = ""
    BLOCKS: Tuple[str, ...] = ()
    FIELD_SPECS: Tuple[Dict[str, Any], ...] = ()
    FIELDS: Tuple[str, ...] = ()
    REQUIRED: Tuple[str, ...] = ()
    CONSTRAINTS: Dict[str, Dict[str, Any]] = {}
    ALLOWED_VALUES: Dict[str, Tuple[Any, ...]] = {}

    def __init__(self, **data: Any) -> None:
        self.id: Optional[int] = data.get("id")
        self.tenant_id: Optional[str] = data.get("tenant_id")
        self.created_at: Optional[str] = data.get("created_at")
        self.updated_at: Optional[str] = data.get("updated_at")
        for name in type(self).FIELDS:
            setattr(self, name, data.get(name))

    @classmethod
    def from_dict(cls, data: Optional[Mapping[str, Any]]) -> "Model":
        return cls(**{str(k): v for k, v in dict(data or {}).items()})

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"id": self.id}
        if self.tenant_id is not None:
            out["tenant_id"] = self.tenant_id
        for name in type(self).FIELDS:
            out[name] = getattr(self, name, None)
        if self.created_at is not None:
            out["created_at"] = self.created_at
        if self.updated_at is not None:
            out["updated_at"] = self.updated_at
        return out

    @classmethod
    def required_fields(cls) -> Tuple[str, ...]:
        return cls.REQUIRED

    @classmethod
    def vocabulary(cls, field: str) -> Tuple[Any, ...]:
        return tuple(cls.ALLOWED_VALUES.get(field, ()))

    @classmethod
    def field_specs(cls) -> List[Dict[str, Any]]:
        return [dict(spec) for spec in cls.FIELD_SPECS]

    @classmethod
    def to_contract(cls) -> Dict[str, Any]:
        """What the console and the acceptance harness read about an entity."""
        return {
            "capability_id": cls.CAPABILITY_ID,
            "entity": cls.ENTITY,
            "title": cls.TITLE,
            "description": cls.DESCRIPTION,
            "blocks": list(cls.BLOCKS),
            "fields": cls.field_specs(),
            "fields_required": list(cls.REQUIRED),
            "statuses": list(ENVELOPE_STATUS_VALUES),
        }


def build_model(
    capability_id: str,
    title: str,
    description: str,
    domain_fields: Sequence[Dict[str, Any]],
    *,
    blocks: Sequence[str] = (),
) -> type:
    """Build one model class from its field specs (envelope appended last)."""
    specs = list(domain_fields) + _envelope()
    names: Tuple[str, ...] = tuple(str(spec["name"]) for spec in specs)
    constraints: Dict[str, Dict[str, Any]] = {}
    for spec in specs:
        rules: Dict[str, Any] = {"type": spec.get("type", "str")}
        if spec.get("required"):
            rules["required"] = True
        if spec.get("allowed_values"):
            rules["allowed_values"] = list(spec["allowed_values"])
        for key in ("min", "max", "min_length", "max_length", "format", "note"):
            if spec.get(key) is not None:
                rules[key] = spec[key]
        constraints[str(spec["name"])] = rules
    required = tuple(str(spec["name"]) for spec in specs if spec.get("required"))
    vocabulary = {
        str(spec["name"]): tuple(spec["allowed_values"])
        for spec in specs
        if spec.get("allowed_values")
    }
    return type(
        capability_id.title().replace("_", ""),
        (Model,),
        {
            "CAPABILITY_ID": capability_id,
            "TITLE": title,
            "ENTITY": capability_id,
            "DESCRIPTION": description,
            "BLOCKS": tuple(blocks),
            "FIELD_SPECS": tuple(specs),
            "FIELDS": names,
            "REQUIRED": required,
            "CONSTRAINTS": constraints,
            "ALLOWED_VALUES": vocabulary,
            "__annotations__": {
                str(spec["name"]): PYTHON_TYPES.get(
                    str(spec.get("type") or "str").strip().lower(), "str"
                )
                for spec in specs
            },
            "__doc__": f"{title}: one row per {capability_id.replace('_', ' ')} event.",
        },
    )


LEAD_INTAKE = [
    _field("lead_name", required=True,  maximum_length=160, note="the person being called"),
    _field("phone", required=True, maximum_length=40, note="as it arrived on the brokerage file"),
    _field("project_tag", required=True, maximum_length=80, note="which PSI project the lead is for"),
    _field("language", allowed_values=LANGUAGES, note="script and ASR language"),
    _field("campaign", maximum_length=80, note="the dialling campaign this lead belongs to"),
    _field("source_file", maximum_length=200, note="the uploaded lead file this came from"),
    _field("lead_email", format="email", maximum_length=200),
    _field("property_type", allowed_values=PROPERTY_TYPES),
    _field("budget", type="float", minimum=0),
    _field("area", maximum_length=120, note="area of interest, free text"),
    _field("timeline", allowed_values=TIMELINES),
    _field("priority", type="int", minimum=1, maximum=5),
    _field("phone_e164", maximum_length=20, note="set when the number normalises"),
    _field("dialable", type="bool", note="false when the number cannot be dialled"),
    _field("dialable_reason", maximum_length=200),
    _field("attempt_count", type="int", minimum=0, maximum=20),
    _field("max_attempts", type="int", minimum=1, maximum=10, note="the brief's ceiling is 3"),
    _field("retry_backoff_minutes", type="int", minimum=0),
    _field("daily_call_cap", type="int", minimum=0, note="campaign reserve policy at intake"),
    _field("concurrency", type="int", minimum=1),
    _field("queue_state", allowed_values=("queued", "dialing", "dialed", "held", "exhausted", "closed")),
    _field("best_call_window", maximum_length=40),
    _field("window_state", allowed_values=("open", "closed")),
    _field("dial_scheduled_at", maximum_length=40),
    _field("next_attempt_at", maximum_length=40),
    _field("last_call_sid", maximum_length=64),
    _field("notes", type="str", maximum_length=2000),
]

CALL_STATE = [
    _field("call_sid", required=True, maximum_length=64, note="Twilio's Call SID is the key"),
    _field("lead_id", maximum_length=40),
    _field("lead_reference", maximum_length=80),
    _field("event", required=True, allowed_values=(
        "dial", "answer", "pitch", "qualify", "transfer", "callback", "close",
        "abandon", "retry", "no_answer", "busy",
    )),
    _field("previous_state", allowed_values=CALL_STATES),
    _field("current_state", allowed_values=CALL_STATES),
    _field("attempt_count", type="int", minimum=0),
    _field("within_window", type="bool"),
    _field("window_reason", maximum_length=60),
    _field("transition_allowed", type="bool"),
    _field("refusal_reason", maximum_length=200),
    _field("guard_notes", maximum_length=400),
    _field("window_snapshot", maximum_length=200),
    _field("occurred_at", maximum_length=40),
    _field("source", allowed_values=("voice_gateway", "operator", "scheduler", "tests"), note="which edge raised this event"),
    _field("campaign", maximum_length=80),
]

GROUNDING = [
    _field("project_tag", required=True, maximum_length=80),
    _field("question", required=True, maximum_length=600, note="what the caller asked"),
    _field("claim_type", allowed_values=(
        "price", "payment_plan", "handover_date", "amenities", "location", "availability",
    )),
    _field("language", allowed_values=LANGUAGES),
    _field("answer", maximum_length=4000, note="null when the corpus cannot support it"),
    _field("pitch", maximum_length=4000, note="the turn the voice edge speaks"),
    _field("citations", note="JSON list of cited chunks"),
    _field("source_documents", maximum_length=600),
    _field("retrieved_count", type="int", minimum=0),
    _field("withheld", type="bool"),
    _field("withheld_claims", maximum_length=400),
    _field("authority_layer", maximum_length=40),
    _field("authority_label", maximum_length=200),
    _field("divergence", maximum_length=2000),
    _field("campaign", maximum_length=80),
]

VOICE = [
    _field("call_sid", required=True, maximum_length=64),
    _field("to_number", required=True, maximum_length=40),
    _field("voice_action", allowed_values=("originate", "gather", "status_callback", "hangup"),
           note="what the edge was asked to do; the reserved word action is never a domain field"),
    _field("from_number", maximum_length=40),
    _field("direction", allowed_values=("outbound", "inbound")),
    _field("language", allowed_values=LANGUAGES),
    _field("call_status", allowed_values=TWILIO_CALL_STATUSES),
    _field("call_event", maximum_length=40, note="the Twilio status callback that arrived"),
    _field("transition_to", allowed_values=CALL_STATES),
    _field("mapping_ok", type="bool"),
    _field("twiml", maximum_length=4000),
    _field("asr_transcript", maximum_length=4000),
    _field("tts_text", maximum_length=2000),
    _field("tts_voice", maximum_length=60),
    _field("gather_language", maximum_length=12),
    _field("conference_sid", maximum_length=64),
    _field("duration_seconds", type="int", minimum=0),
    _field("attempt", type="int", minimum=0),
    _field("provider", maximum_length=40),
    _field("call_key_source", maximum_length=40),
    _field("edge_stub", type="bool"),
    _field("unavailable_blocks", maximum_length=400),
]

WARM_TRANSFER = [
    _field("call_sid", required=True, maximum_length=64),
    _field("outcome", required=True, allowed_values=(
        "transferred", "declined", "broker_unavailable", "no_qualification", "failed",
    )),
    _field("lead_id", maximum_length=40),
    _field("project_tag", maximum_length=80),
    _field("qualified_outcome", allowed_values=OUTCOMES[:3]),
    _field("broker_number", maximum_length=40),
    _field("broker_language", allowed_values=LANGUAGES),
    _field("whisper_text", maximum_length=2000, note="spoken to the broker leg only"),
    _field("summary", note="JSON: the structured broker summary"),
    _field("steps", note="JSON: the bridge sequence actually attempted"),
    _field("step_count", type="int", minimum=0),
    _field("conference_name", maximum_length=80),
    _field("conference_sid", maximum_length=64),
    _field("bridge_seconds", type="int", minimum=0),
    _field("attempt", type="int", minimum=0),
    _field("transfer_key", maximum_length=80, note="call_sid + lead, for dedup"),
    _field("edge_stub", type="bool"),
    _field("unavailable_blocks", maximum_length=400),
]

QUALIFICATION = [
    _field("call_sid", required=True, maximum_length=64),
    _field("outcome", required=True, allowed_values=OUTCOMES[:3], note="the brief's three outcomes"),
    _field("language", allowed_values=LANGUAGES),
    _field("project_tag", maximum_length=80),
    _field("lead_name", maximum_length=160),
    _field("property_type", allowed_values=PROPERTY_TYPES),
    _field("budget", type="float", minimum=0),
    _field("currency", maximum_length=8, note="from CURRENCY; unset when the operator has not stated it"),
    _field("area", maximum_length=120),
    _field("timeline", allowed_values=TIMELINES),
    _field("transcript", maximum_length=4000, note="the call excerpt the qualification came from"),
    _field("collected", note="JSON: property_type/budget/area/timeline as collected"),
    _field("summary", note="JSON: the structured broker summary"),
    _field("summary_text", maximum_length=2000),
    _field("recommendation", maximum_length=600),
    _field("next_action", allowed_values=("transfer_to_broker", "schedule_callback", "close_lead", "nurture")),
    _field("qualified", type="bool"),
    _field("transfer_required", type="bool"),
    _field("authority_layer", maximum_length=40),
    _field("authority_label", maximum_length=200),
    _field("campaign", maximum_length=80),
]

LEDGER = [
    _field("call_sid", required=True, maximum_length=64),
    _field("event_type", required=True, allowed_values=(
        "attempted", "initiated", "ringing", "answered", "pitched", "qualified",
        "outcome_recorded", "transfer_started", "transfer_completed", "call_ended",
    )),
    _field("sequence", type="int", minimum=1),
    _field("prev_hash", maximum_length=64),
    _field("entry_hash", maximum_length=64),
    _field("payload_digest", maximum_length=64),
    _field("outcome", allowed_values=OUTCOMES),
    _field("actor", maximum_length=80),
    _field("campaign", maximum_length=80),
    _field("detail", note="JSON: the event payload as hashed"),
    _field("chain_ok", type="bool"),
    _field("verified_count", type="int", minimum=0),
]

CRM = [
    _field("call_sid", required=True, maximum_length=64),
    _field("crm_system", maximum_length=60, note="unstated by the brief; null until named"),
    _field("destination", maximum_length=200),
    _field("destination_named", type="bool"),
    _field("payload_shape", note="JSON: the shape that would be sent, never a claim it was"),
    _field("delivery", allowed_values=("placeholder", "activated", "blocked", "unavailable")),
    _field("unavailable_blocks", maximum_length=400),
    _field("outcome", allowed_values=OUTCOMES),
    _field("summary", note="JSON: the broker summary that would accompany the outcome"),
    _field("note", maximum_length=400),
    _field("intended_method", allowed_values=("POST", "PUT", "PATCH")),
]

NOTIFICATION = [
    _field("trigger_event", required=True, allowed_values=(
        "lead_qualified", "transfer_completed", "call_failed", "attempt_exhausted",
        "campaign_summary",
    )),
    _field("channel", allowed_values=("webhook", "slack", "sms", "email")),
    _field("target", maximum_length=300, note="where the ping goes (operator setting)"),
    _field("subject", maximum_length=200),
    _field("body", maximum_length=4000),
    _field("delivery", allowed_values=("delivered", "queued", "stubbed", "unavailable", "refused")),
    _field("provider", maximum_length=60),
    _field("attempts", type="int", minimum=0),
    _field("response_code", type="int", minimum=0),
    _field("delivered_at", maximum_length=40),
    _field("unavailable_blocks", maximum_length=400),
    _field("message_digest", maximum_length=64),
    _field("summary", note="JSON: the broker summary carried with the alert"),
    _field("outcome", allowed_values=OUTCOMES),
    _field("call_sid", maximum_length=64),
    _field("campaign", maximum_length=80),
]

LOCAL_DRIVE = [
    _field("operation", required=True, allowed_values=("put", "get", "list", "delete", "stat")),
    _field("relative_path", required=True, maximum_length=300, note="relative to the tenant's root"),
    _field("content", maximum_length=20000),
    _field("content_digest", maximum_length=64),
    _field("bytes_written", type="int", minimum=0),
    _field("root", maximum_length=300),
    _field("tenant_root", maximum_length=300),
    _field("entries", note="JSON: directory listing"),
    _field("file_exists", type="bool"),
    _field("size_bytes", type="int", minimum=0),
    _field("media_type", maximum_length=120),
]

GOOGLE_DRIVE = [
    _field("operation", required=True, allowed_values=("upload", "download", "list", "search", "share", "delete")),
    _field("drive_mode", allowed_values=("stubbed", "live")),
    _field("folder_id", maximum_length=120),
    _field("document_id", maximum_length=120),
    _field("file_name", maximum_length=200),
    _field("mime_type", maximum_length=120),
    _field("credentials_present", type="bool"),
    _field("unavailable_blocks", maximum_length=400),
    _field("delivery", allowed_values=("stub", "unavailable", "delivered")),
    _field("note", maximum_length=400),
    _field("would_call", maximum_length=300),
    _field("upload_state", maximum_length=40),
]

MCP = [
    _field("method", required=True, allowed_values=("tools/list", "tools/call", "tools/describe", "resources/list")),
    _field("tool", maximum_length=80),
    _field("arguments", note="JSON: the JSON-RPC arguments"),
    _field("catalog_scope", allowed_values=("platform", "tenant")),
    _field("result", note="JSON: the JSON-RPC result"),
    _field("tool_count", type="int", minimum=0),
    _field("dispatched", type="bool"),
    _field("error_code", maximum_length=40),
    _field("protocol", maximum_length=40),
    _field("duration_ms", type="int", minimum=0),
]


MODELS: Dict[str, type] = {
    model.CAPABILITY_ID: model
    for model in (
        build_model(
            "lead_intake_and_dial_queue",
            "Lead intake & dial queue",
            "CSV/Excel lead files parsed into durable dial-list rows: name, phone, "
            "language, project tag, with cap/backoff/window policy attached.",
            LEAD_INTAKE,
            blocks=("capture", "queue", "formula_executor", "validation"),
        ),
        build_model(
            "call_state_machine",
            "Call state machine",
            "Each lead's call lifecycle as an explicit state machine keyed to the "
            "Call SID, with the call-window schedule enforced as a transition guard.",
            CALL_STATE,
            blocks=("workflow", "orchestrator", "event_bus"),
        ),
        build_model(
            "project_knowledge_grounding",
            "Project knowledge grounding",
            "Project sheets pitched per project tag with cite-or-refuse: price, "
            "payment plan and handover date are quoted from retrieved text or withheld.",
            GROUNDING,
            blocks=("knowledge", "vector_search", "ingestion_provenance", "evidence_or_refuse", "llm_enhancer"),
        ),
        build_model(
            "voice_gateway",
            "Voice gateway (Twilio edge)",
            "Originate, ASR gather in English and Arabic, Polly Neural TTS, and "
            "status-callback events mapped onto workflow transitions by Call SID.",
            VOICE,
            blocks=(),
        ),
        build_model(
            "warm_transfer",
            "Warm transfer",
            "Collect the summary, dial the broker leg, whisper the summary to the "
            "broker only, bridge both legs, return the transfer outcome.",
            WARM_TRANSFER,
            blocks=(),
        ),
        build_model(
            "qualification_and_broker_summary",
            "Qualification & broker summary",
            "Outcome is one enum (project_interested, other_re_interested, "
            "not_interested) beside collected fields; the broker summary is built from it.",
            QUALIFICATION,
            blocks=("validation", "recommendation_template", "knowledge"),
        ),
        build_model(
            "outcome_capture_and_ledger",
            "Outcome capture & ledger",
            "Every call outcome persists through the route, and each event is "
            "appended to a hash-chained ledger reconstructable per Call SID.",
            LEDGER,
            blocks=("audit_chain", "database", "storage", "agent_state_sync"),
        ),
        build_model(
            "crm_destination_placeholder",
            "CRM destination placeholder",
            "The CRM destination is unstated, so this records intent and payload "
            "shape and never claims a delivery that did not happen.",
            CRM,
            blocks=("mock_connector_bus", "webhook"),
        ),
        build_model(
            "notification",
            "Notification",
            "Pings the broker / sales channel the moment a lead qualifies, over the "
            "operator's webhook; stubbed with a named blocker when none is set.",
            NOTIFICATION,
            blocks=("notification",),
        ),
        build_model(
            "local_drive",
            "Local drive",
            "Tenant-scoped file store for ingested project sheets, with a path "
            "traversal guard and content digests.",
            LOCAL_DRIVE,
            blocks=("local_drive",),
        ),
        build_model(
            "google_drive",
            "Google Drive",
            "Drive connector. Ships declaring unavailable_blocks until the operator "
            "supplies credentials; the request shape is built and tested against a fake transport.",
            GOOGLE_DRIVE,
            blocks=("google_drive",),
        ),
        build_model(
            "mcp_adapter",
            "MCP adapter",
            "JSON-RPC MCP surface over this platform's own capabilities: tools/list, "
            "tools/describe and tools/call dispatched in-process as the caller's tenant.",
            MCP,
            blocks=("mcp_adapter",),
        ),
    )
}

CAPABILITY_IDS: Tuple[str, ...] = tuple(MODELS)

#: Blocks the blueprint assigns to capabilities no single capability owns.
PLATFORM_BLOCKS: Tuple[str, ...] = (
    "twilio_programmable_voice",
    "grpc_orchestrator",
    "chart_renderer",
)


def model_for(capability_id: str) -> type:
    try:
        return MODELS[str(capability_id)]
    except KeyError as exc:
        raise KeyError(f"unknown capability: {capability_id}") from exc


def contract_catalog() -> List[Dict[str, Any]]:
    return [MODELS[cap].to_contract() for cap in CAPABILITY_IDS]
