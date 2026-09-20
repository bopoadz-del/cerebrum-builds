"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AutoAssignment:
    """Entity for capability auto_assignment."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    complaint_reference: str = ""
    school: str = ""
    category: str = 'electrical'
    priority: str = 'critical'
    required_trade: str = ""
    required_skill: str = ""
    candidate_count: int = 0
    assigned_to: str = ""
    assigned_role: str = 'technician'
    assignment_mode: str = 'auto'
    match_score: int = 0
    workload_score: int = 0
    queue_position: int = 0
    override_reason: str = ""
    assigned_at: str = '2026-09-03T10:00:00'

    FIELDS = ['reference', 'status', 'complaint_reference', 'school', 'category', 'priority', 'required_trade', 'required_skill', 'candidate_count', 'assigned_to', 'assigned_role', 'assignment_mode', 'match_score', 'workload_score', 'queue_position', 'override_reason', 'assigned_at']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'complaint_reference': {'required': True}, 'school': {'required': True}, 'category': {'allowed_values': ['electrical', 'plumbing', 'hvac', 'cleaning', 'safety', 'grounds', 'furniture', 'it_av', 'pest_control', 'other'], 'required': True}, 'priority': {'allowed_values': ['critical', 'high', 'medium', 'low'], 'required': True}, 'required_trade': {'required': True}, 'required_skill': {'required': False}, 'candidate_count': {'min': 0, 'max': 500, 'required': False}, 'assigned_to': {'required': False}, 'assigned_role': {'allowed_values': ['technician', 'cleaner', 'supervisor'], 'required': False}, 'assignment_mode': {'allowed_values': ['auto', 'manual', 'unassigned'], 'required': True}, 'match_score': {'min': 0, 'max': 100, 'required': False}, 'workload_score': {'min': 0, 'max': 100, 'required': False}, 'queue_position': {'min': 0, 'max': 10000, 'required': False}, 'override_reason': {'required': False}, 'assigned_at': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutoAssignment":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class BookingSystemIntegration:
    """Entity for capability booking_system_integration."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    integration: str = 'booking_system'
    mode: str = 'placeholder'
    booking_reference: str = ""
    school: str = ""
    facility: str = ""
    slot_start: str = '2026-09-03T10:00:00'
    slot_end: str = '2026-09-03T10:00:00'
    requested_by: str = ""
    sync_state: str = 'not_implemented'
    last_sync_at: str = '2026-09-03T10:00:00'
    detail: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'integration', 'mode', 'booking_reference', 'school', 'facility', 'slot_start', 'slot_end', 'requested_by', 'sync_state', 'last_sync_at', 'detail', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'integration': {'allowed_values': ['booking_system'], 'required': True}, 'mode': {'allowed_values': ['placeholder'], 'required': True}, 'booking_reference': {'required': True}, 'school': {'required': True}, 'facility': {'required': True}, 'slot_start': {'required': True}, 'slot_end': {'required': False}, 'requested_by': {'required': False}, 'sync_state': {'allowed_values': ['not_implemented', 'queued', 'blocked'], 'required': False}, 'last_sync_at': {'required': False}, 'detail': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookingSystemIntegration":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ComplaintsManagement:
    """Entity for capability complaints_management."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    school: str = ""
    site_code: str = ""
    category: str = 'electrical'
    priority: str = 'critical'
    description: str = ""
    raised_by: str = ""
    raised_by_role: str = 'school_staff'
    contact_email: str = ""
    contact_phone: str = ""
    logged_by: str = ""
    assigned_to: str = ""
    assignment_mode: str = 'auto'
    reported_at: str = '2026-09-03T10:00:00'
    due_at: str = '2026-09-03T10:00:00'
    sla_hours: int = 1
    closed_at: str = '2026-09-03T10:00:00'
    resolution_notes: str = ""
    work_order_reference: str = ""

    FIELDS = ['reference', 'status', 'school', 'site_code', 'category', 'priority', 'description', 'raised_by', 'raised_by_role', 'contact_email', 'contact_phone', 'logged_by', 'assigned_to', 'assignment_mode', 'reported_at', 'due_at', 'sla_hours', 'closed_at', 'resolution_notes', 'work_order_reference']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'school': {'required': True}, 'site_code': {'required': False}, 'category': {'allowed_values': ['electrical', 'plumbing', 'hvac', 'cleaning', 'safety', 'grounds', 'furniture', 'it_av', 'pest_control', 'other'], 'required': True}, 'priority': {'allowed_values': ['critical', 'high', 'medium', 'low'], 'required': True}, 'description': {'required': True}, 'raised_by': {'required': True}, 'raised_by_role': {'allowed_values': ['school_staff', 'parent', 'management', 'student'], 'required': True}, 'contact_email': {'required': False}, 'contact_phone': {'required': False}, 'logged_by': {'required': False}, 'assigned_to': {'required': False}, 'assignment_mode': {'allowed_values': ['auto', 'manual', 'unassigned'], 'required': False}, 'reported_at': {'required': False}, 'due_at': {'required': False}, 'sla_hours': {'min': 1, 'max': 720, 'required': False}, 'closed_at': {'required': False}, 'resolution_notes': {'required': False}, 'work_order_reference': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplaintsManagement":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ErpIntegration:
    """Entity for capability erp_integration."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    integration: str = 'erp'
    mode: str = 'placeholder'
    entity_type: str = 'purchase_order'
    direction: str = 'inbound'
    external_reference: str = ""
    endpoint: str = ""
    currency: str = ""
    amount: float = 0
    sync_state: str = 'not_implemented'
    last_sync_at: str = '2026-09-03T10:00:00'
    detail: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'integration', 'mode', 'entity_type', 'direction', 'external_reference', 'endpoint', 'currency', 'amount', 'sync_state', 'last_sync_at', 'detail', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'integration': {'allowed_values': ['erp'], 'required': True}, 'mode': {'allowed_values': ['placeholder'], 'required': True}, 'entity_type': {'allowed_values': ['purchase_order', 'invoice', 'vendor', 'staff_roster', 'asset'], 'required': True}, 'direction': {'allowed_values': ['inbound', 'outbound'], 'required': True}, 'external_reference': {'required': False}, 'endpoint': {'required': False}, 'currency': {'required': False}, 'amount': {'min': 0, 'max': 100000000, 'required': False}, 'sync_state': {'allowed_values': ['not_implemented', 'queued', 'blocked'], 'required': False}, 'last_sync_at': {'required': False}, 'detail': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErpIntegration":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ManagementDashboards:
    """Entity for capability management_dashboards."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    scope: str = 'school'
    school: str = ""
    period: str = ""
    complaints_open: int = 0
    complaints_in_progress: int = 0
    complaints_closed: int = 0
    jobs_in_progress: int = 0
    sla_breaches: int = 0
    sla_compliance_pct: float = 0
    avg_closure_hours: float = 0
    headline: str = ""
    generated_at: str = '2026-09-03T10:00:00'

    FIELDS = ['reference', 'status', 'scope', 'school', 'period', 'complaints_open', 'complaints_in_progress', 'complaints_closed', 'jobs_in_progress', 'sla_breaches', 'sla_compliance_pct', 'avg_closure_hours', 'headline', 'generated_at']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'scope': {'allowed_values': ['school', 'portfolio'], 'required': True}, 'school': {'required': True}, 'period': {'required': True}, 'complaints_open': {'min': 0, 'max': 100000, 'required': True}, 'complaints_in_progress': {'min': 0, 'max': 100000, 'required': False}, 'complaints_closed': {'min': 0, 'max': 100000, 'required': False}, 'jobs_in_progress': {'min': 0, 'max': 100000, 'required': False}, 'sla_breaches': {'min': 0, 'max': 100000, 'required': False}, 'sla_compliance_pct': {'min': 0, 'max': 100, 'required': False}, 'avg_closure_hours': {'min': 0, 'max': 10000, 'required': False}, 'headline': {'required': False}, 'generated_at': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManagementDashboards":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class Reporting:
    """Entity for capability reporting."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    report_type: str = 'daily'
    scope: str = 'school'
    school: str = ""
    period_start: str = '2026-09-03'
    period_end: str = '2026-09-03'
    complaints_total: int = 0
    closed_total: int = 0
    avg_closure_hours: float = 0
    sla_compliance_pct: float = 0
    top_category: str = ""
    busiest_school: str = ""
    recipients: str = ""
    generated_at: str = '2026-09-03T10:00:00'

    FIELDS = ['reference', 'status', 'report_type', 'scope', 'school', 'period_start', 'period_end', 'complaints_total', 'closed_total', 'avg_closure_hours', 'sla_compliance_pct', 'top_category', 'busiest_school', 'recipients', 'generated_at']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'report_type': {'allowed_values': ['daily', 'weekly', 'monthly', 'on_demand'], 'required': True}, 'scope': {'allowed_values': ['school', 'portfolio'], 'required': True}, 'school': {'required': True}, 'period_start': {'required': True}, 'period_end': {'required': True}, 'complaints_total': {'min': 0, 'max': 1000000, 'required': True}, 'closed_total': {'min': 0, 'max': 1000000, 'required': False}, 'avg_closure_hours': {'min': 0, 'max': 100000, 'required': False}, 'sla_compliance_pct': {'min': 0, 'max': 100, 'required': False}, 'top_category': {'required': False}, 'busiest_school': {'required': False}, 'recipients': {'required': False}, 'generated_at': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reporting":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class RoleBasedAccess:
    """Entity for capability role_based_access."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    principal: str = ""
    principal_email: str = ""
    role: str = 'management'
    school: str = ""
    access_scope: str = 'portfolio'
    permissions: str = ""
    granted_by: str = ""
    effective_from: str = '2026-09-03'
    last_review_at: str = '2026-09-03T10:00:00'
    active: bool = False
    notes: str = ""

    FIELDS = ['reference', 'status', 'principal', 'principal_email', 'role', 'school', 'access_scope', 'permissions', 'granted_by', 'effective_from', 'last_review_at', 'active', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'principal': {'required': True}, 'principal_email': {'required': False}, 'role': {'allowed_values': ['management', 'admin', 'technician', 'cleaner', 'complainant', 'school_staff'], 'required': True}, 'school': {'required': True}, 'access_scope': {'allowed_values': ['portfolio', 'school', 'assigned_jobs', 'own_complaints'], 'required': True}, 'permissions': {'required': False}, 'granted_by': {'required': False}, 'effective_from': {'required': False}, 'last_review_at': {'required': False}, 'active': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoleBasedAccess":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class WorkforceManagement:
    """Entity for capability workforce_management."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    school: str = ""
    team_name: str = ""
    team_type: str = 'technician'
    trade: str = ""
    shift: str = 'morning'
    headcount: int = 1
    lead_name: str = ""
    lead_email: str = ""
    contact_phone: str = ""
    active: bool = False
    open_jobs: int = 0
    notes: str = ""

    FIELDS = ['reference', 'status', 'school', 'team_name', 'team_type', 'trade', 'shift', 'headcount', 'lead_name', 'lead_email', 'contact_phone', 'active', 'open_jobs', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'school': {'required': True}, 'team_name': {'required': True}, 'team_type': {'allowed_values': ['technician', 'cleaner', 'supervisor', 'mixed'], 'required': True}, 'trade': {'required': False}, 'shift': {'allowed_values': ['morning', 'afternoon', 'night', 'split'], 'required': True}, 'headcount': {'min': 1, 'max': 500, 'required': True}, 'lead_name': {'required': False}, 'lead_email': {'required': False}, 'contact_phone': {'required': False}, 'active': {'required': False}, 'open_jobs': {'min': 0, 'max': 10000, 'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkforceManagement":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {
    "auto_assignment": AutoAssignment,
    "booking_system_integration": BookingSystemIntegration,
    "complaints_management": ComplaintsManagement,
    "erp_integration": ErpIntegration,
    "management_dashboards": ManagementDashboards,
    "reporting": Reporting,
    "role_based_access": RoleBasedAccess,
    "workforce_management": WorkforceManagement,
}
