"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PatientVisitRecords:
    """Entity for capability patient_visit_records."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    tooth: str = ""
    procedure: str = ""
    fee: float = 0.0
    visit_date: str = '2026-09-03'
    provider: str = ""
    clinical_notes: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'tooth', 'procedure', 'fee', 'visit_date', 'provider', 'clinical_notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'tooth': {'required': True}, 'procedure': {'required': True}, 'fee': {'min': 0.0, 'max': 100000.0, 'required': False}, 'visit_date': {'format': 'date', 'required': False}, 'provider': {'required': False}, 'clinical_notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatientVisitRecords":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


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
    notes: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'patient_email', 'scheduled_at', 'provider', 'chair_room', 'appointment_type', 'duration_minutes', 'reminder_channel', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'patient_email': {'format': 'email', 'required': False}, 'scheduled_at': {'format': 'datetime', 'required': False}, 'provider': {'required': False}, 'chair_room': {'required': False}, 'appointment_type': {'allowed_values': ['exam', 'hygiene', 'treatment', 'follow_up', 'emergency'], 'required': True}, 'duration_minutes': {'min': 5, 'max': 480, 'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}, 'notes': {'required': False}}
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
class TodaysAppointmentList:
    """Entity for capability todays_appointment_list."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    list_date: str = '2026-09-03'
    patient_name: str = ""
    provider: str = ""
    procedure: str = ""
    appointment_time: str = '10:00:00'
    appointment_status: str = 'scheduled'
    chair_room: str = ""

    FIELDS = ['reference', 'status', 'list_date', 'patient_name', 'provider', 'procedure', 'appointment_time', 'appointment_status', 'chair_room']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'list_date': {'format': 'date', 'required': True}, 'patient_name': {'required': True}, 'provider': {'required': False}, 'procedure': {'required': False}, 'appointment_time': {'format': 'time', 'required': False}, 'appointment_status': {'allowed_values': ['scheduled', 'checked_in', 'completed', 'cancelled'], 'required': False}, 'chair_room': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TodaysAppointmentList":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class DayBeforeEmailReminders:
    """Entity for capability day_before_email_reminders."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    patient_email: str = ""
    reminder_date: str = '2026-09-03'
    appointment_at: str = '2026-09-03T10:00:00'
    reminder_channel: str = 'email'
    message_body: str = ""
    delivery_state: str = 'queued'

    FIELDS = ['reference', 'status', 'patient_name', 'patient_email', 'reminder_date', 'appointment_at', 'reminder_channel', 'message_body', 'delivery_state']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'patient_email': {'format': 'email', 'required': True}, 'reminder_date': {'format': 'date', 'required': True}, 'appointment_at': {'format': 'datetime', 'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}, 'message_body': {'required': False}, 'delivery_state': {'allowed_values': ['queued', 'sent', 'skipped', 'cancelled'], 'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DayBeforeEmailReminders":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class PatientDirectory:
    """Entity for capability patient_directory."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    patient_email: str = ""
    patient_phone: str = ""
    date_of_birth: str = '2026-09-03'
    primary_provider: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'patient_email', 'patient_phone', 'date_of_birth', 'primary_provider', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'patient_email': {'format': 'email', 'required': False}, 'patient_phone': {'required': False}, 'date_of_birth': {'format': 'date', 'required': False}, 'primary_provider': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatientDirectory":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ClinicalHistorySearch:
    """Entity for capability clinical_history_search."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    tooth: str = ""
    procedure: str = ""
    provider: str = ""
    visit_date: str = '2026-09-03'
    date_from: str = '2026-09-03'
    date_to: str = '2026-09-03'
    search_notes: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'tooth', 'procedure', 'provider', 'visit_date', 'date_from', 'date_to', 'search_notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'tooth': {'required': False}, 'procedure': {'required': False}, 'provider': {'required': False}, 'visit_date': {'format': 'date', 'required': False}, 'date_from': {'format': 'date', 'required': False}, 'date_to': {'format': 'date', 'required': False}, 'search_notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClinicalHistorySearch":
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
    staff_name: str = ""
    staff_email: str = ""
    staff_role: str = 'dentist'
    permission_scope: str = ""
    active_from: str = '2026-09-03'

    FIELDS = ['reference', 'status', 'staff_name', 'staff_email', 'staff_role', 'permission_scope', 'active_from']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'staff_name': {'required': True}, 'staff_email': {'format': 'email', 'required': False}, 'staff_role': {'allowed_values': ['dentist', 'hygienist', 'receptionist', 'admin'], 'required': True}, 'permission_scope': {'required': False}, 'active_from': {'format': 'date', 'required': False}}
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


MODELS = {
    "patient_visit_records": PatientVisitRecords,
    "appointment_scheduling": AppointmentScheduling,
    "todays_appointment_list": TodaysAppointmentList,
    "day_before_email_reminders": DayBeforeEmailReminders,
    "patient_directory": PatientDirectory,
    "clinical_history_search": ClinicalHistorySearch,
    "role_based_access": RoleBasedAccess,
}
