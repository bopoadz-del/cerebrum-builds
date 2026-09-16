"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ClientIntake:
    """Entity for capability client_intake."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    client_name: str = ""
    client_email: str = ""
    client_phone: str = ""
    matter_type: str = ""
    referral_source: str = ""
    conflict_check: str = ""
    risk_score: float = 0.0
    estimated_fee: float = 0.0
    retainer_amount: float = 0.0
    document_path: str = ""
    intake_date: str = '2026-09-03'

    FIELDS = ['reference', 'status', 'client_name', 'client_email', 'client_phone', 'matter_type', 'referral_source', 'conflict_check', 'risk_score', 'estimated_fee', 'retainer_amount', 'document_path', 'intake_date']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'client_name': {'required': True}, 'client_email': {'required': False}, 'client_phone': {'required': False}, 'matter_type': {'required': False}, 'referral_source': {'required': False}, 'conflict_check': {'required': False}, 'risk_score': {'required': False}, 'estimated_fee': {'required': False}, 'retainer_amount': {'required': False}, 'document_path': {'required': False}, 'intake_date': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientIntake":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ClientPortal:
    """Entity for capability client_portal."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    client_name: str = ""
    client_email: str = ""
    matter_number: str = ""
    portal_access_level: str = ""
    unread_messages: int = 0
    shared_documents: int = 0
    message_subject: str = ""
    message_body: str = ""
    last_login_at: str = '2026-09-03T10:00:00'
    document_path: str = ""

    FIELDS = ['reference', 'status', 'client_name', 'client_email', 'matter_number', 'portal_access_level', 'unread_messages', 'shared_documents', 'message_subject', 'message_body', 'last_login_at', 'document_path']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'client_name': {'required': True}, 'client_email': {'required': False}, 'matter_number': {'required': False}, 'portal_access_level': {'required': False}, 'unread_messages': {'min': 0, 'max': 10000, 'required': False}, 'shared_documents': {'min': 0, 'max': 10000, 'required': False}, 'message_subject': {'required': False}, 'message_body': {'required': False}, 'last_login_at': {'required': False}, 'document_path': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientPortal":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ComplianceAudit:
    """Entity for capability compliance_audit."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    control_id: str = ""
    framework: str = ""
    regulation: str = ""
    event_type: str = ""
    actor: str = ""
    actor_role: str = ""
    action_taken: str = ""
    evidence_ref: str = ""
    findings: str = ""
    occurred_at: str = '2026-09-03T10:00:00'

    FIELDS = ['reference', 'status', 'control_id', 'framework', 'regulation', 'event_type', 'actor', 'actor_role', 'action_taken', 'evidence_ref', 'findings', 'occurred_at']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'control_id': {'required': True}, 'framework': {'required': False}, 'regulation': {'required': False}, 'event_type': {'required': False}, 'actor': {'required': False}, 'actor_role': {'required': False}, 'action_taken': {'required': False}, 'evidence_ref': {'required': False}, 'findings': {'required': False}, 'occurred_at': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplianceAudit":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class DocumentManagement:
    """Entity for capability document_management."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    document_title: str = ""
    document_type: str = ""
    matter_number: str = ""
    version: str = ""
    file_path: str = ""
    content_hash: str = ""
    confidentiality: str = ""
    document_owner: str = ""
    tags: str = ""
    uploaded_by: str = ""
    uploaded_at: str = '2026-09-03T10:00:00'

    FIELDS = ['reference', 'status', 'document_title', 'document_type', 'matter_number', 'version', 'file_path', 'content_hash', 'confidentiality', 'document_owner', 'tags', 'uploaded_by', 'uploaded_at']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'document_title': {'required': True}, 'document_type': {'required': False}, 'matter_number': {'required': False}, 'version': {'required': False}, 'file_path': {'required': False}, 'content_hash': {'required': False}, 'confidentiality': {'required': False}, 'document_owner': {'required': False}, 'tags': {'required': False}, 'uploaded_by': {'required': False}, 'uploaded_at': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentManagement":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class LegalAnalytics:
    """Entity for capability legal_analytics."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    metric_name: str = ""
    metric_value: float = 0.0
    benchmark_value: float = 0.0
    practice_area: str = ""
    dimension: str = ""
    period_start: str = '2026-09-03'
    period_end: str = '2026-09-03'
    source_matter: str = ""

    FIELDS = ['reference', 'status', 'metric_name', 'metric_value', 'benchmark_value', 'practice_area', 'dimension', 'period_start', 'period_end', 'source_matter']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'metric_name': {'required': True}, 'metric_value': {'required': False}, 'benchmark_value': {'required': False}, 'practice_area': {'required': False}, 'dimension': {'required': False}, 'period_start': {'required': False}, 'period_end': {'required': False}, 'source_matter': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalAnalytics":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class MatterManagement:
    """Entity for capability matter_management."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    matter_number: str = ""
    matter_title: str = ""
    client_name: str = ""
    client_email: str = ""
    practice_area: str = ""
    responsible_attorney: str = ""
    matter_stage: str = ""
    priority: str = ""
    opened_date: str = '2026-09-03'
    deadline_date: str = '2026-09-03'
    billing_type: str = ""
    document_path: str = ""

    FIELDS = ['reference', 'status', 'matter_number', 'matter_title', 'client_name', 'client_email', 'practice_area', 'responsible_attorney', 'matter_stage', 'priority', 'opened_date', 'deadline_date', 'billing_type', 'document_path']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'matter_number': {'required': True}, 'matter_title': {'required': True}, 'client_name': {'required': True}, 'client_email': {'required': False}, 'practice_area': {'required': False}, 'responsible_attorney': {'required': False}, 'matter_stage': {'required': False}, 'priority': {'required': False}, 'opened_date': {'required': False}, 'deadline_date': {'required': False}, 'billing_type': {'required': False}, 'document_path': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatterManagement":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class TimeAndBilling:
    """Entity for capability time_and_billing."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    timekeeper: str = ""
    matter_number: str = ""
    client_name: str = ""
    client_email: str = ""
    activity_date: str = '2026-09-03'
    hours: float = 0.0
    hourly_rate: float = 0.0
    billable_amount: float = 0.0
    invoice_number: str = ""
    payment_status: str = ""
    narrative: str = ""

    FIELDS = ['reference', 'status', 'timekeeper', 'matter_number', 'client_name', 'client_email', 'activity_date', 'hours', 'hourly_rate', 'billable_amount', 'invoice_number', 'payment_status', 'narrative']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'timekeeper': {'required': True}, 'matter_number': {'required': True}, 'client_name': {'required': False}, 'client_email': {'required': False}, 'activity_date': {'required': False}, 'hours': {'min': 0.0, 'max': 1000.0, 'required': False}, 'hourly_rate': {'min': 0.0, 'max': 5000.0, 'required': False}, 'billable_amount': {'required': False}, 'invoice_number': {'required': False}, 'payment_status': {'required': False}, 'narrative': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeAndBilling":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {
    "client_intake": ClientIntake,
    "client_portal": ClientPortal,
    "compliance_audit": ComplianceAudit,
    "document_management": DocumentManagement,
    "legal_analytics": LegalAnalytics,
    "matter_management": MatterManagement,
    "time_and_billing": TimeAndBilling,
}
