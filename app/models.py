"""Domain models for the CallOps voice platform.

Plain dataclasses on purpose: the delivered platform runs with no ORM,
no database server and no network. Persistence is app/store.py; the
schema is alembic/versions/0001_baseline.py.

Every entity carries the envelope ``reference`` / ``status``, and the
status vocabulary is the schema-enforced one: open | in_progress |
closed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class LeadIntakeAndDialQueue:
    """Entity for capability lead_intake_and_dial_queue."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    lead_name: str = ""
    phone: str = ""
    language: str = 'en'
    project_tag: str = ""
    source_file: str = ""
    call_window: str = ""
    daily_call_cap: int = 0
    concurrency: int = 0
    attempt_count: int = 0
    retry_backoff_minutes: int = 0
    queue_status: str = 'queued'
    notes: str = ""

    FIELDS = ['reference', 'status', 'lead_name', 'phone', 'language', 'project_tag', 'source_file', 'call_window', 'daily_call_cap', 'concurrency', 'attempt_count', 'retry_backoff_minutes', 'queue_status', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'lead_name': {'required': True}, 'phone': {'required': True}, 'language': {'allowed_values': ['en', 'ar'], 'required': True}, 'project_tag': {'required': True}, 'source_file': {'required': False}, 'call_window': {'required': False}, 'daily_call_cap': {'min': 1, 'max': 100000, 'required': False, 'type': 'int'}, 'concurrency': {'min': 1, 'max': 50, 'required': False, 'type': 'int'}, 'attempt_count': {'min': 0, 'max': 3, 'required': False, 'type': 'int'}, 'retry_backoff_minutes': {'min': 0, 'max': 1440, 'required': False, 'type': 'int'}, 'queue_status': {'allowed_values': ['queued', 'dialing', 'paused', 'exhausted'], 'required': False}, 'notes': {'required': False}}
    ENTITY = "lead_intake_and_dial_queue"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeadIntakeAndDialQueue":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class CallStateMachine:
    """Entity for capability call_state_machine."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    call_sid: str = ""
    lead_name: str = ""
    phone: str = ""
    current_state: str = 'queued'
    previous_state: str = 'queued'
    call_window: str = ""
    window_state: str = 'open'
    transition_event: str = ""
    attempt_count: int = 0
    notes: str = ""

    FIELDS = ['reference', 'status', 'call_sid', 'lead_name', 'phone', 'current_state', 'previous_state', 'call_window', 'window_state', 'transition_event', 'attempt_count', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'call_sid': {'required': True}, 'lead_name': {'required': False}, 'phone': {'required': False}, 'current_state': {'allowed_values': ['queued', 'dialing', 'answered', 'pitched', 'qualified', 'transferred', 'callback', 'closed'], 'required': True}, 'previous_state': {'allowed_values': ['queued', 'dialing', 'answered', 'pitched', 'qualified', 'transferred', 'callback', 'closed'], 'required': False}, 'call_window': {'required': False}, 'window_state': {'allowed_values': ['open', 'closed'], 'required': False}, 'transition_event': {'required': False}, 'attempt_count': {'min': 0, 'max': 3, 'required': False, 'type': 'int'}, 'notes': {'required': False}}
    ENTITY = "call_state_machine"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallStateMachine":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ProjectKnowledgeGrounding:
    """Entity for capability project_knowledge_grounding."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    project_tag: str = ""
    claim_type: str = 'price'
    question: str = ""
    document_name: str = ""
    document_text: str = ""
    citation: str = ""
    authority_label: str = 'certified'
    grounded: bool = False
    answer: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'project_tag', 'claim_type', 'question', 'document_name', 'document_text', 'citation', 'authority_label', 'grounded', 'answer', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'project_tag': {'required': True}, 'claim_type': {'allowed_values': ['price', 'payment_plan', 'handover_date', 'other'], 'required': True}, 'question': {'required': True}, 'document_name': {'required': False}, 'document_text': {'required': False}, 'citation': {'required': False}, 'authority_label': {'allowed_values': ['certified', 'documents', 'formulas', 'procedures'], 'required': False}, 'grounded': {'required': False, 'type': 'bool'}, 'answer': {'required': False}, 'notes': {'required': False}}
    ENTITY = "project_knowledge_grounding"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectKnowledgeGrounding":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class VoiceGateway:
    """Entity for capability voice_gateway."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    call_sid: str = ""
    direction: str = 'outbound'
    to_number: str = ""
    from_number: str = ""
    language: str = 'en'
    voice: str = ""
    asr_engine: str = 'twilio_gather_speech'
    twilio_mode: str = 'stubbed'
    call_status: str = 'initiated'
    twiml: str = ""
    recording_url: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'call_sid', 'direction', 'to_number', 'from_number', 'language', 'voice', 'asr_engine', 'twilio_mode', 'call_status', 'twiml', 'recording_url', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'call_sid': {'required': False}, 'direction': {'allowed_values': ['outbound', 'inbound'], 'required': False}, 'to_number': {'required': False}, 'from_number': {'required': False}, 'language': {'allowed_values': ['en', 'ar'], 'required': True}, 'voice': {'required': False}, 'asr_engine': {'allowed_values': ['twilio_gather_speech'], 'required': False}, 'twilio_mode': {'allowed_values': ['stubbed', 'live'], 'required': False}, 'call_status': {'allowed_values': ['initiated', 'ringing', 'answered', 'completed', 'failed', 'busy', 'no-answer'], 'required': False}, 'twiml': {'required': False}, 'recording_url': {'required': False}, 'notes': {'required': False}}
    ENTITY = "voice_gateway"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceGateway":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class WarmTransfer:
    """Entity for capability warm_transfer."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    call_sid: str = ""
    lead_name: str = ""
    outcome: str = 'project_interested'
    broker_number: str = ""
    conference_name: str = ""
    summary: str = ""
    whisper_text: str = ""
    transfer_status: str = 'initiated'
    whisper_delivered: bool = False
    notes: str = ""

    FIELDS = ['reference', 'status', 'call_sid', 'lead_name', 'outcome', 'broker_number', 'conference_name', 'summary', 'whisper_text', 'transfer_status', 'whisper_delivered', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'call_sid': {'required': True}, 'lead_name': {'required': False}, 'outcome': {'allowed_values': ['project_interested', 'other_re_interested', 'not_interested'], 'required': True}, 'broker_number': {'required': False}, 'conference_name': {'required': False}, 'summary': {'required': True}, 'whisper_text': {'required': False}, 'transfer_status': {'allowed_values': ['initiated', 'bridged', 'failed', 'declined'], 'required': False}, 'whisper_delivered': {'required': False, 'type': 'bool'}, 'notes': {'required': False}}
    ENTITY = "warm_transfer"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WarmTransfer":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class QualificationAndBrokerSummary:
    """Entity for capability qualification_and_broker_summary."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    call_sid: str = ""
    lead_name: str = ""
    outcome: str = 'project_interested'
    property_type: str = 'apartment'
    budget: float = 0.0
    area: str = ""
    timeline: str = ""
    currency_setting: str = ""
    broker_summary: str = ""
    recommended_action: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'call_sid', 'lead_name', 'outcome', 'property_type', 'budget', 'area', 'timeline', 'currency_setting', 'broker_summary', 'recommended_action', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'call_sid': {'required': True}, 'lead_name': {'required': False}, 'outcome': {'allowed_values': ['project_interested', 'other_re_interested', 'not_interested'], 'required': True}, 'property_type': {'allowed_values': ['apartment', 'villa', 'townhouse', 'plot', 'office'], 'required': False}, 'budget': {'min': 0.0, 'required': False, 'type': 'float'}, 'area': {'required': False}, 'timeline': {'required': False}, 'currency_setting': {'required': False}, 'broker_summary': {'required': False}, 'recommended_action': {'required': False}, 'notes': {'required': False}}
    ENTITY = "qualification_and_broker_summary"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualificationAndBrokerSummary":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class OutcomeCaptureAndLedger:
    """Entity for capability outcome_capture_and_ledger."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    call_sid: str = ""
    campaign: str = ""
    event_type: str = 'attempt'
    outcome: str = 'project_interested'
    attempt_count: int = 0
    ledger_index: int = 0
    vector_clock: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'call_sid', 'campaign', 'event_type', 'outcome', 'attempt_count', 'ledger_index', 'vector_clock', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'call_sid': {'required': True}, 'campaign': {'required': False}, 'event_type': {'allowed_values': ['attempt', 'answer', 'outcome', 'transfer', 'disposition'], 'required': True}, 'outcome': {'allowed_values': ['project_interested', 'other_re_interested', 'not_interested'], 'required': False}, 'attempt_count': {'min': 0, 'max': 3, 'required': False, 'type': 'int'}, 'ledger_index': {'min': 0, 'required': False, 'type': 'int'}, 'vector_clock': {'required': False}, 'notes': {'required': False}}
    ENTITY = "outcome_capture_and_ledger"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutcomeCaptureAndLedger":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class CrmDestinationPlaceholder:
    """Entity for capability crm_destination_placeholder."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    crm_system: str = 'unstated'
    destination_url: str = ""
    payload_shape: str = ""
    delivery_state: str = 'queued'
    mock_mode: bool = False
    notes: str = ""

    FIELDS = ['reference', 'status', 'crm_system', 'destination_url', 'payload_shape', 'delivery_state', 'mock_mode', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'crm_system': {'allowed_values': ['unstated', 'salesforce', 'hubspot', 'zoho'], 'required': True}, 'destination_url': {'required': False}, 'payload_shape': {'required': False}, 'delivery_state': {'allowed_values': ['queued', 'stubbed', 'refused'], 'required': False}, 'mock_mode': {'required': False, 'type': 'bool'}, 'notes': {'required': False}}
    ENTITY = "crm_destination_placeholder"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrmDestinationPlaceholder":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class Notification:
    """Entity for capability notification."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    channel: str = 'email'
    recipient: str = ""
    subject: str = ""
    message: str = ""
    trigger_event: str = 'lead_qualified'
    delivery_state: str = 'queued'
    notes: str = ""

    FIELDS = ['reference', 'status', 'channel', 'recipient', 'subject', 'message', 'trigger_event', 'delivery_state', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'channel': {'allowed_values': ['email', 'sms', 'mcp', 'webhook'], 'required': True}, 'recipient': {'required': False}, 'subject': {'required': False}, 'message': {'required': False}, 'trigger_event': {'allowed_values': ['lead_qualified', 'transfer_completed', 'call_failed', 'campaign_summary'], 'required': True}, 'delivery_state': {'allowed_values': ['queued', 'sent', 'failed'], 'required': False}, 'notes': {'required': False}}
    ENTITY = "notification"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Notification":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class LocalDrive:
    """Entity for capability local_drive."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    root_path: str = ""
    relative_path: str = ""
    operation: str = 'read'
    bytes_written: int = 0
    content_preview: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'root_path', 'relative_path', 'operation', 'bytes_written', 'content_preview', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'root_path': {'required': False}, 'relative_path': {'required': True}, 'operation': {'allowed_values': ['read', 'write', 'list', 'delete'], 'required': True}, 'bytes_written': {'min': 0, 'required': False, 'type': 'int'}, 'content_preview': {'required': False}, 'notes': {'required': False}}
    ENTITY = "local_drive"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalDrive":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class GoogleDrive:
    """Entity for capability google_drive.

    ``GOOGLE_CLIENT_ID`` / ``GOOGLE_CLIENT_SECRET`` / ``GOOGLE_REFRESH_TOKEN``
    are declared on this entity as OPTIONAL settings: the connector names them
    as the settings that turn the live path on, and the connector reads them
    from the process environment. They are not required fields -- a caller
    cannot be asked for a deploy-time credential, and requiring them here made
    this capability refuse a payload built from its own schema
    (``Missing required field: GOOGLE_CLIENT_ID``). Leave them empty and the
    connector runs stubbed and says so; set them in the environment and the
    same code path calls Google. They are treated as credential material
    everywhere else -- never logged, never echoed by /health.
    """

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    drive_mode: str = 'stubbed'
    folder_id: str = ""
    file_name: str = ""
    operation: str = 'upload'
    credential_setting: str = ""
    #: Operator credential material, named as the connector reads it from the
    #: environment. The connector reads these from ``os.environ``; they are
    #: optional on the record (deploy-time settings, not caller fields), so a
    #: schema-sample POST needs none of them and the connector still runs
    #: stubbed until the operator sets them.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REFRESH_TOKEN: str = ""
    notes: str = ""

    FIELDS = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REFRESH_TOKEN', 'reference', 'status', 'drive_mode', 'folder_id', 'file_name', 'operation', 'credential_setting', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'drive_mode': {'allowed_values': ['stubbed', 'live'], 'required': True}, 'folder_id': {'required': False}, 'file_name': {'required': False}, 'operation': {'allowed_values': ['upload', 'download', 'list'], 'required': True}, 'credential_setting': {'required': False}, 'GOOGLE_CLIENT_ID': {'required': False}, 'GOOGLE_CLIENT_SECRET': {'required': False}, 'GOOGLE_REFRESH_TOKEN': {'required': False}, 'notes': {'required': False}}
    ENTITY = "google_drive"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoogleDrive":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class McpAdapter:
    """Entity for capability mcp_adapter."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    tool_name: str = ""
    catalog_scope: str = 'platform'
    request_shape: str = ""
    response_shape: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'tool_name', 'catalog_scope', 'request_shape', 'response_shape', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'tool_name': {'required': False}, 'catalog_scope': {'allowed_values': ['platform', 'vendor', 'tenant'], 'required': True}, 'request_shape': {'required': False}, 'response_shape': {'required': False}, 'notes': {'required': False}}
    ENTITY = "mcp_adapter"
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "McpAdapter":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


#: capability_id -> its model, in the order the platform declares them.
MODELS = {"lead_intake_and_dial_queue": LeadIntakeAndDialQueue, "call_state_machine": CallStateMachine, "project_knowledge_grounding": ProjectKnowledgeGrounding, "voice_gateway": VoiceGateway, "warm_transfer": WarmTransfer, "qualification_and_broker_summary": QualificationAndBrokerSummary, "outcome_capture_and_ledger": OutcomeCaptureAndLedger, "crm_destination_placeholder": CrmDestinationPlaceholder, "notification": Notification, "local_drive": LocalDrive, "google_drive": GoogleDrive, "mcp_adapter": McpAdapter}
