"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class BudgetPlanningTracking:
    """Entity for capability budget_planning_tracking."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    department: str = ""
    budget_owner: str = ""
    cost_centre: str = ""
    period: str = ""
    planned_amount: float = 0
    actual_amount: float = 0
    currency: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'department', 'budget_owner', 'cost_centre', 'period', 'planned_amount', 'actual_amount', 'currency', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'department': {'required': True}, 'budget_owner': {'required': True}, 'cost_centre': {'required': False}, 'period': {'required': False}, 'planned_amount': {'required': False, 'min': 0}, 'actual_amount': {'required': False, 'min': 0}, 'currency': {'required': False}, 'notes': {'required': False}}
    REQUIRED = ['reference', 'status', 'department', 'budget_owner']
    _FIELD_PY: Dict[str, str] = field(default_factory=dict)
    _FIELD_JSON: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BudgetPlanningTracking":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)

@dataclass
class SpendCaptureCategorisation:
    """Entity for capability spend_capture_categorisation."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    department: str = ""
    supplier: str = ""
    category: str = ""
    amount: float = 0
    currency: str = ""
    invoice_date: str = ""
    invoice_number: str = ""
    document_path: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'department', 'supplier', 'category', 'amount', 'currency', 'invoice_date', 'invoice_number', 'document_path', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'department': {'required': True}, 'supplier': {'required': True}, 'category': {'required': True, 'allowed_values': ['software', 'travel', 'facilities', 'professional_services', 'marketing']}, 'amount': {'required': False, 'min': 0}, 'currency': {'required': False}, 'invoice_date': {'required': False}, 'invoice_number': {'required': False}, 'document_path': {'required': False}, 'notes': {'required': False}}
    REQUIRED = ['reference', 'status', 'department', 'supplier', 'category']
    _FIELD_PY: Dict[str, str] = field(default_factory=dict)
    _FIELD_JSON: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpendCaptureCategorisation":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)

@dataclass
class ApprovalWorkflow:
    """Entity for capability approval_workflow."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    department: str = ""
    request_type: str = ""
    approver: str = ""
    approver_email: str = ""
    amount: float = 0
    threshold: float = 0
    priority: str = ""
    submitted_at: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'department', 'request_type', 'approver', 'approver_email', 'amount', 'threshold', 'priority', 'submitted_at', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'department': {'required': True}, 'request_type': {'required': True, 'allowed_values': ['invoice', 'expense', 'budget_change']}, 'approver': {'required': True}, 'approver_email': {'required': False}, 'amount': {'required': False, 'min': 0}, 'threshold': {'required': False, 'min': 0}, 'priority': {'required': False, 'allowed_values': ['low', 'normal', 'high', 'urgent']}, 'submitted_at': {'required': False}, 'notes': {'required': False}}
    REQUIRED = ['reference', 'status', 'department', 'request_type', 'approver']
    _FIELD_PY: Dict[str, str] = field(default_factory=dict)
    _FIELD_JSON: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalWorkflow":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)

@dataclass
class VarianceAnalytics:
    """Entity for capability variance_analytics."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    department: str = ""
    category: str = ""
    period: str = ""
    budget_amount: float = 0
    actual_amount: float = 0
    formula: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'department', 'category', 'period', 'budget_amount', 'actual_amount', 'formula', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'department': {'required': True}, 'category': {'required': False}, 'period': {'required': False}, 'budget_amount': {'required': False, 'min': 0}, 'actual_amount': {'required': False, 'min': 0}, 'formula': {'required': False}, 'notes': {'required': False}}
    REQUIRED = ['reference', 'status', 'department']
    _FIELD_PY: Dict[str, str] = field(default_factory=dict)
    _FIELD_JSON: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VarianceAnalytics":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)

@dataclass
class DashboardPortfolioRollup:
    """Entity for capability dashboard_portfolio_rollup."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    department: str = ""
    role_view: str = ""
    view_scope: str = ""
    period: str = ""
    spend_total: float = 0
    commitment_total: float = 0
    forecast_total: float = 0
    risk_level: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'department', 'role_view', 'view_scope', 'period', 'spend_total', 'commitment_total', 'forecast_total', 'risk_level', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'department': {'required': True}, 'role_view': {'required': True, 'allowed_values': ['cfo', 'controller', 'budget_owner']}, 'view_scope': {'required': False}, 'period': {'required': False}, 'spend_total': {'required': False, 'min': 0}, 'commitment_total': {'required': False, 'min': 0}, 'forecast_total': {'required': False, 'min': 0}, 'risk_level': {'required': False, 'allowed_values': ['low', 'medium', 'high']}, 'notes': {'required': False}}
    REQUIRED = ['reference', 'status', 'department', 'role_view']
    _FIELD_PY: Dict[str, str] = field(default_factory=dict)
    _FIELD_JSON: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DashboardPortfolioRollup":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)

@dataclass
class AuditEvidenceValidation:
    """Entity for capability audit_evidence_validation."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    department: str = ""
    record_type: str = ""
    record_reference: str = ""
    evidence_hash: str = ""
    verified: bool = False
    checked_at: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'department', 'record_type', 'record_reference', 'evidence_hash', 'verified', 'checked_at', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'department': {'required': True}, 'record_type': {'required': True, 'allowed_values': ['invoice', 'expense', 'approval', 'budget']}, 'record_reference': {'required': True}, 'evidence_hash': {'required': False}, 'verified': {'required': False}, 'checked_at': {'required': False}, 'notes': {'required': False}}
    REQUIRED = ['reference', 'status', 'department', 'record_type', 'record_reference']
    _FIELD_PY: Dict[str, str] = field(default_factory=dict)
    _FIELD_JSON: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvidenceValidation":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)

@dataclass
class FinanceDocumentKnowledge:
    """Entity for capability finance_document_knowledge."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    department: str = ""
    document_type: str = ""
    question: str = ""
    answer: str = ""
    citations: str = ""
    confidence: float = 0
    document_path: str = ""

    FIELDS = ['reference', 'status', 'department', 'document_type', 'question', 'answer', 'citations', 'confidence', 'document_path']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'department': {'required': True}, 'document_type': {'required': True, 'allowed_values': ['invoice', 'contract', 'policy', 'price_list']}, 'question': {'required': True}, 'answer': {'required': False}, 'citations': {'required': False}, 'confidence': {'required': False, 'min': 0, 'max': 1}, 'document_path': {'required': False}}
    REQUIRED = ['reference', 'status', 'department', 'document_type', 'question']
    _FIELD_PY: Dict[str, str] = field(default_factory=dict)
    _FIELD_JSON: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FinanceDocumentKnowledge":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)

@dataclass
class IntegrationsPlaceholders:
    """Entity for capability integrations_placeholders."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    department: str = ""
    integration: str = ""
    direction: str = ""
    detail: str = ""
    external_reference: str = ""
    last_sync_at: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'department', 'integration', 'direction', 'detail', 'external_reference', 'last_sync_at', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'required': True, 'allowed_values': ['open', 'in_progress', 'closed']}, 'department': {'required': True}, 'integration': {'required': True, 'allowed_values': ['google_drive', 'sage', 'email_slack']}, 'direction': {'required': True, 'allowed_values': ['inbound', 'outbound']}, 'detail': {'required': False}, 'external_reference': {'required': False}, 'last_sync_at': {'required': False}, 'notes': {'required': False}}
    REQUIRED = ['reference', 'status', 'department', 'integration', 'direction']
    _FIELD_PY: Dict[str, str] = field(default_factory=dict)
    _FIELD_JSON: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntegrationsPlaceholders":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)

MODELS = {
    "budget_planning_tracking": BudgetPlanningTracking,
    "spend_capture_categorisation": SpendCaptureCategorisation,
    "approval_workflow": ApprovalWorkflow,
    "variance_analytics": VarianceAnalytics,
    "dashboard_portfolio_rollup": DashboardPortfolioRollup,
    "audit_evidence_validation": AuditEvidenceValidation,
    "finance_document_knowledge": FinanceDocumentKnowledge,
    "integrations_placeholders": IntegrationsPlaceholders,
}

__all__ = ["MODELS", 'BudgetPlanningTracking', 'SpendCaptureCategorisation', 'ApprovalWorkflow', 'VarianceAnalytics', 'DashboardPortfolioRollup', 'AuditEvidenceValidation', 'FinanceDocumentKnowledge', 'IntegrationsPlaceholders']
