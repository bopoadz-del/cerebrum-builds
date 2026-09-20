"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class JobAndSiteTracking:
    """Entity for capability job_and_site_tracking."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    job_code: str = ""
    job_name: str = ""
    site_name: str = ""
    client_name: str = ""
    work_front: str = ""
    contract_value_aed: float = 0.0
    progress_percent: float = 0.0
    milestone: str = ""
    milestone_due_date: str = ""
    snag_open_count: int = 0
    variation_reference: str = ""
    variation_status: str = 'draft'
    notes: str = ""

    FIELDS = ['reference', 'status', 'job_code', 'job_name', 'site_name', 'client_name', 'work_front', 'contract_value_aed', 'progress_percent', 'milestone', 'milestone_due_date', 'snag_open_count', 'variation_reference', 'variation_status', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'job_code': {'required': True}, 'job_name': {'required': True}, 'site_name': {'required': True}, 'client_name': {'required': False}, 'work_front': {'required': False}, 'contract_value_aed': {'required': False, 'min': 0, 'max': 1000000000}, 'progress_percent': {'required': False, 'min': 0, 'max': 100}, 'milestone': {'required': False}, 'milestone_due_date': {'required': False, 'format': 'date'}, 'snag_open_count': {'required': False, 'min': 0, 'max': 10000}, 'variation_reference': {'required': False}, 'variation_status': {'required': False, 'allowed_values': ['draft', 'submitted', 'approved', 'rejected']}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobAndSiteTracking":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class CommercialsAndValuations:
    """Entity for capability commercials_and_valuations."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    valuation_number: str = ""
    job_code: str = ""
    boq_item: str = ""
    measured_quantity: float = 0.0
    unit_rate_aed: float = 0.0
    gross_value_aed: float = 0.0
    retention_percent: float = 0.0
    retention_aed: float = 0.0
    vat_rate_percent: float = 0.0
    vat_amount_aed: float = 0.0
    certified_value_aed: float = 0.0
    payment_status: str = 'unpaid'
    purchase_order: str = ""
    po_party_type: str = 'supplier'
    amount_due_aed: float = 0.0
    due_on: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'valuation_number', 'job_code', 'boq_item', 'measured_quantity', 'unit_rate_aed', 'gross_value_aed', 'retention_percent', 'retention_aed', 'vat_rate_percent', 'vat_amount_aed', 'certified_value_aed', 'payment_status', 'purchase_order', 'po_party_type', 'amount_due_aed', 'due_on', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'valuation_number': {'required': True}, 'job_code': {'required': True}, 'boq_item': {'required': False}, 'measured_quantity': {'required': False, 'min': 0, 'max': 10000000}, 'unit_rate_aed': {'required': False, 'min': 0, 'max': 10000000}, 'gross_value_aed': {'required': False, 'min': 0, 'max': 1000000000}, 'retention_percent': {'required': False, 'min': 0, 'max': 100}, 'retention_aed': {'required': False, 'min': 0, 'max': 1000000000}, 'vat_rate_percent': {'required': False, 'min': 0, 'max': 100}, 'vat_amount_aed': {'required': False, 'min': 0, 'max': 1000000000}, 'certified_value_aed': {'required': False, 'min': 0, 'max': 1000000000}, 'payment_status': {'required': False, 'allowed_values': ['unpaid', 'partial', 'paid']}, 'purchase_order': {'required': False}, 'po_party_type': {'required': False, 'allowed_values': ['supplier', 'subcontractor']}, 'amount_due_aed': {'required': False, 'min': 0, 'max': 1000000000}, 'due_on': {'required': False, 'format': 'date'}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommercialsAndValuations":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class DocumentQaAndIndexing:
    """Entity for capability document_qa_and_indexing."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    document_title: str = ""
    document_type: str = 'boq'
    job_code: str = ""
    revision: str = ""
    file_name: str = ""
    file_path: str = ""
    file_sha256: str = ""
    question: str = ""
    answer: str = ""
    source_reference: str = ""
    indexed_at: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'document_title', 'document_type', 'job_code', 'revision', 'file_name', 'file_path', 'file_sha256', 'question', 'answer', 'source_reference', 'indexed_at', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'document_title': {'required': True}, 'document_type': {'required': True, 'allowed_values': ['boq', 'drawing', 'method_statement', 'safety_procedure', 'price_list', 'subcontract', 'other']}, 'job_code': {'required': False}, 'revision': {'required': False}, 'file_name': {'required': False}, 'file_path': {'required': False}, 'file_sha256': {'required': False}, 'question': {'required': False}, 'answer': {'required': False}, 'source_reference': {'required': False}, 'indexed_at': {'required': False, 'format': 'datetime'}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentQaAndIndexing":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class SafetyAndCompliance:
    """Entity for capability safety_and_compliance."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    job_code: str = ""
    document_title: str = ""
    method_statement_ref: str = ""
    work_front: str = ""
    checklist_item: str = ""
    checklist_state: str = 'met'
    readiness_gate: str = 'ready'
    incident_type: str = 'near_miss'
    incident_date: str = ""
    severity: str = 'low'
    action_taken: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'job_code', 'document_title', 'method_statement_ref', 'work_front', 'checklist_item', 'checklist_state', 'readiness_gate', 'incident_type', 'incident_date', 'severity', 'action_taken', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'job_code': {'required': True}, 'document_title': {'required': True}, 'method_statement_ref': {'required': False}, 'work_front': {'required': False}, 'checklist_item': {'required': False}, 'checklist_state': {'required': False, 'allowed_values': ['met', 'unmet']}, 'readiness_gate': {'required': False, 'allowed_values': ['ready', 'blocked', 'not_assessed']}, 'incident_type': {'required': False, 'allowed_values': ['near_miss', 'incident', 'hazard']}, 'incident_date': {'required': False, 'format': 'date'}, 'severity': {'required': False, 'allowed_values': ['low', 'medium', 'high']}, 'action_taken': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SafetyAndCompliance":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ProgressCostDashboard:
    """Entity for capability progress_cost_dashboard."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    report_date: str = ""
    job_code: str = ""
    progress_percent: float = 0.0
    certified_value_aed: float = 0.0
    cost_to_date_aed: float = 0.0
    variations_pending: int = 0
    snags_open: int = 0
    payments_due_aed: float = 0.0
    margin_percent: float = -100.0
    summary: str = ""

    FIELDS = ['reference', 'status', 'report_date', 'job_code', 'progress_percent', 'certified_value_aed', 'cost_to_date_aed', 'variations_pending', 'snags_open', 'payments_due_aed', 'margin_percent', 'summary']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'report_date': {'required': True, 'format': 'date'}, 'job_code': {'required': True}, 'progress_percent': {'required': False, 'min': 0, 'max': 100}, 'certified_value_aed': {'required': False, 'min': 0, 'max': 1000000000}, 'cost_to_date_aed': {'required': False, 'min': 0, 'max': 1000000000}, 'variations_pending': {'required': False, 'min': 0, 'max': 10000}, 'snags_open': {'required': False, 'min': 0, 'max': 10000}, 'payments_due_aed': {'required': False, 'min': 0, 'max': 1000000000}, 'margin_percent': {'required': False, 'min': -100, 'max': 100}, 'summary': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressCostDashboard":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class AutomationRemindersEscalation:
    """Entity for capability automation_reminders_escalation."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    job_code: str = ""
    reminder_type: str = 'valuation_due'
    due_date: str = ""
    threshold_count: int = 0
    actual_count: int = 0
    escalation_state: str = 'none'
    channel: str = 'email'
    recipient_email: str = ""
    message_body: str = ""
    schedule: str = 'monthly'
    summary: str = ""

    FIELDS = ['reference', 'status', 'job_code', 'reminder_type', 'due_date', 'threshold_count', 'actual_count', 'escalation_state', 'channel', 'recipient_email', 'message_body', 'schedule', 'summary']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'job_code': {'required': True}, 'reminder_type': {'required': True, 'allowed_values': ['valuation_due', 'variation_escalation', 'snag_escalation', 'overdue_payment']}, 'due_date': {'required': False, 'format': 'date'}, 'threshold_count': {'required': False, 'min': 0, 'max': 10000}, 'actual_count': {'required': False, 'min': 0, 'max': 10000}, 'escalation_state': {'required': False, 'allowed_values': ['none', 'flagged', 'escalated']}, 'channel': {'required': False, 'allowed_values': ['email', 'webhook', 'slack']}, 'recipient_email': {'required': False}, 'message_body': {'required': False}, 'schedule': {'required': False, 'allowed_values': ['monthly', 'weekly', 'daily']}, 'summary': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutomationRemindersEscalation":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class AuditAndAccessControl:
    """Entity for capability audit_and_access_control."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    actor_name: str = ""
    actor_role: str = 'owner'
    action_type: str = 'approval'
    entity_name: str = ""
    entity_reference: str = ""
    change_summary: str = ""
    approval_state: str = 'pending'
    occurred_at: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'actor_name', 'actor_role', 'action_type', 'entity_name', 'entity_reference', 'change_summary', 'approval_state', 'occurred_at', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'actor_name': {'required': True}, 'actor_role': {'required': True, 'allowed_values': ['owner', 'site_engineer', 'accounts', 'admin']}, 'action_type': {'required': True, 'allowed_values': ['approval', 'document_version', 'financial_change', 'access_grant', 'access_revoke']}, 'entity_name': {'required': False}, 'entity_reference': {'required': False}, 'change_summary': {'required': False}, 'approval_state': {'required': False, 'allowed_values': ['pending', 'approved', 'rejected']}, 'occurred_at': {'required': False, 'format': 'datetime'}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditAndAccessControl":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class TeamNotifications:
    """Entity for capability team_notifications."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    recipient_email: str = ""
    recipient_role: str = 'owner'
    channel: str = 'email'
    subject: str = ""
    message_body: str = ""
    notification_type: str = 'approval'
    related_reference: str = ""
    send_at: str = ""
    delivery_state: str = 'queued'

    FIELDS = ['reference', 'status', 'recipient_email', 'recipient_role', 'channel', 'subject', 'message_body', 'notification_type', 'related_reference', 'send_at', 'delivery_state']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'recipient_email': {'required': False}, 'recipient_role': {'required': False, 'allowed_values': ['owner', 'site_engineer', 'accounts']}, 'channel': {'required': False, 'allowed_values': ['email', 'slack', 'webhook']}, 'subject': {'required': True}, 'message_body': {'required': True}, 'notification_type': {'required': False, 'allowed_values': ['approval', 'valuation_due', 'overdue_item', 'snag']}, 'related_reference': {'required': False}, 'send_at': {'required': False, 'format': 'datetime'}, 'delivery_state': {'required': False, 'allowed_values': ['queued', 'sent', 'skipped']}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamNotifications":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {
    "audit_and_access_control": AuditAndAccessControl,
    "automation_reminders_escalation": AutomationRemindersEscalation,
    "commercials_and_valuations": CommercialsAndValuations,
    "document_qa_and_indexing": DocumentQaAndIndexing,
    "job_and_site_tracking": JobAndSiteTracking,
    "progress_cost_dashboard": ProgressCostDashboard,
    "safety_and_compliance": SafetyAndCompliance,
    "team_notifications": TeamNotifications,
}
