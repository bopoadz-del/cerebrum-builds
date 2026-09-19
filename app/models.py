"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AppointmentScheduling:
    """Entity for capability appointment_scheduling."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    patient_email: str = ""
    scheduled_at: str = '2026-09-03T10:00:00'
    provider: str = ""
    chair_room: str = ""
    appointment_type: str = 'exam'
    duration_minutes: int = 5
    reminder_channel: str = 'email'
    appointment_status: str = 'scheduled'
    notes: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'patient_email', 'scheduled_at', 'provider', 'chair_room', 'appointment_type', 'duration_minutes', 'reminder_channel', 'appointment_status', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'patient_email': {'format': 'email', 'required': False}, 'scheduled_at': {'format': 'datetime', 'required': False}, 'provider': {'required': False}, 'chair_room': {'required': False}, 'appointment_type': {'allowed_values': ['exam', 'hygiene', 'treatment', 'follow_up', 'emergency'], 'required': True}, 'duration_minutes': {'min': 5, 'max': 480, 'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'in_app'], 'required': False}, 'appointment_status': {'allowed_values': ['scheduled', 'confirmed', 'checked_in', 'completed', 'cancelled'], 'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppointmentScheduling":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ClinicDashboard:
    """Entity for capability clinic_dashboard."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    dashboard_date: str = '2026-09-03'
    appointments_today: int = 0
    patients_seen: int = 0
    outstanding_invoices: int = 0
    recalls_due: int = 0
    chair_utilisation: float = 0.0
    summary: str = ""

    FIELDS = ['reference', 'status', 'dashboard_date', 'appointments_today', 'patients_seen', 'outstanding_invoices', 'recalls_due', 'chair_utilisation', 'summary']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'dashboard_date': {'format': 'date', 'required': False}, 'appointments_today': {'min': 0, 'max': 500, 'required': False}, 'patients_seen': {'min': 0, 'max': 500, 'required': False}, 'outstanding_invoices': {'min': 0, 'max': 5000, 'required': False}, 'recalls_due': {'min': 0, 'max': 5000, 'required': False}, 'chair_utilisation': {'min': 0.0, 'max': 100.0, 'required': False}, 'summary': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClinicDashboard":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class Invoicing:
    """Entity for capability invoicing."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    invoice_number: str = ""
    treatment_code: str = ""
    amount: float = 0.0
    tax_rate: float = 0.0
    total_due: float = 0.0
    payment_status: str = 'unpaid'
    issued_on: str = '2026-09-03'
    due_on: str = '2026-09-03'
    notes: str = ""
    attachment_path: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'invoice_number', 'treatment_code', 'amount', 'tax_rate', 'total_due', 'payment_status', 'issued_on', 'due_on', 'notes', 'attachment_path']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'invoice_number': {'required': False}, 'treatment_code': {'required': False}, 'amount': {'min': 0.0, 'max': 100000.0, 'required': False}, 'tax_rate': {'min': 0.0, 'max': 100.0, 'required': False}, 'total_due': {'min': 0.0, 'max': 200000.0, 'required': False}, 'payment_status': {'allowed_values': ['unpaid', 'partial', 'paid'], 'required': False}, 'issued_on': {'format': 'date', 'required': False}, 'due_on': {'format': 'date', 'required': False}, 'notes': {'required': False}, 'attachment_path': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Invoicing":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class PatientRecords:
    """Entity for capability patient_records."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    patient_email: str = ""
    patient_phone: str = ""
    date_of_birth: str = '2026-09-03'
    address: str = ""
    medical_history: str = ""
    dental_history: str = ""
    insurance_provider: str = ""
    insurance_member_id: str = ""
    primary_provider: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'patient_email', 'patient_phone', 'date_of_birth', 'address', 'medical_history', 'dental_history', 'insurance_provider', 'insurance_member_id', 'primary_provider', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'patient_email': {'format': 'email', 'required': False}, 'patient_phone': {'required': False}, 'date_of_birth': {'format': 'date', 'required': False}, 'address': {'required': False}, 'medical_history': {'required': False}, 'dental_history': {'required': False}, 'insurance_provider': {'required': False}, 'insurance_member_id': {'required': False}, 'primary_provider': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatientRecords":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class RecallReminders:
    """Entity for capability recall_reminders."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    patient_email: str = ""
    recall_interval_months: int = 1
    last_visit_date: str = '2026-09-03'
    due_date: str = '2026-09-03'
    reminder_type: str = 'recall'
    reminder_channel: str = 'email'
    message_body: str = ""
    delivery_state: str = 'queued'

    FIELDS = ['reference', 'status', 'patient_name', 'patient_email', 'recall_interval_months', 'last_visit_date', 'due_date', 'reminder_type', 'reminder_channel', 'message_body', 'delivery_state']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'patient_email': {'format': 'email', 'required': False}, 'recall_interval_months': {'min': 1, 'max': 36, 'required': False}, 'last_visit_date': {'format': 'date', 'required': False}, 'due_date': {'format': 'date', 'required': False}, 'reminder_type': {'allowed_values': ['recall', 'hygiene', 'treatment_follow_up'], 'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'in_app'], 'required': False}, 'message_body': {'required': False}, 'delivery_state': {'allowed_values': ['queued', 'sent', 'skipped', 'cancelled'], 'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecallReminders":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class StaffRolesPermissions:
    """Entity for capability staff_roles_permissions."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    staff_name: str = ""
    staff_email: str = ""
    staff_role: str = 'dentist'
    permission_scope: str = 'full_clinic'
    active_from: str = '2026-09-03'
    active: bool = False

    FIELDS = ['reference', 'status', 'staff_name', 'staff_email', 'staff_role', 'permission_scope', 'active_from', 'active']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'staff_name': {'required': True}, 'staff_email': {'format': 'email', 'required': False}, 'staff_role': {'allowed_values': ['dentist', 'hygienist', 'receptionist', 'admin'], 'required': True}, 'permission_scope': {'allowed_values': ['full_clinic', 'clinical', 'front_desk', 'read_only'], 'required': False}, 'active_from': {'format': 'date', 'required': False}, 'active': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StaffRolesPermissions":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class TreatmentRecords:
    """Entity for capability treatment_records."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    tooth: str = ""
    procedure: str = ""
    provider: str = ""
    treatment_date: str = '2026-09-03'
    clinical_notes: str = ""
    follow_up_date: str = '2026-09-03'
    attachment_name: str = ""
    attachment_path: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'tooth', 'procedure', 'provider', 'treatment_date', 'clinical_notes', 'follow_up_date', 'attachment_name', 'attachment_path']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'tooth': {'required': False}, 'procedure': {'required': True}, 'provider': {'required': False}, 'treatment_date': {'format': 'date', 'required': False}, 'clinical_notes': {'required': False}, 'follow_up_date': {'format': 'date', 'required': False}, 'attachment_name': {'required': False}, 'attachment_path': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreatmentRecords":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {
    "appointment_scheduling": AppointmentScheduling,
    "clinic_dashboard": ClinicDashboard,
    "invoicing": Invoicing,
    "patient_records": PatientRecords,
    "recall_reminders": RecallReminders,
    "staff_roles_permissions": StaffRolesPermissions,
    "treatment_records": TreatmentRecords,
}
