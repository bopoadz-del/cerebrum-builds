"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AnalyticsAndReporting:
    """Entity for capability analytics_and_reporting."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    report_name: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    period_start: str = '2026-09-03'
    period_end: str = '2026-09-03'
    appointments_count: int = 0
    revenue_total: float = 0.0
    event_type: str = ""

    FIELDS = ['reference', 'status', 'report_name', 'metric_name', 'metric_value', 'period_start', 'period_end', 'appointments_count', 'revenue_total', 'event_type']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'report_name': {'required': True}, 'metric_name': {'required': True}, 'metric_value': {'min': 0.0, 'max': 100000000.0, 'required': False}, 'period_start': {'format': 'date', 'required': False}, 'period_end': {'format': 'date', 'required': False}, 'appointments_count': {'min': 0, 'max': 1000000, 'required': False}, 'revenue_total': {'min': 0.0, 'max': 100000000.0, 'required': False}, 'event_type': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalyticsAndReporting":
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
    owner_name: str = ""
    scheduled_at: str = '2026-09-03T10:00:00'
    appointment_type: str = 'wellness_exam'
    veterinarian: str = ""
    room: str = ""
    duration_minutes: int = 5
    reminder_channel: str = 'email'
    notes: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'owner_name', 'scheduled_at', 'appointment_type', 'veterinarian', 'room', 'duration_minutes', 'reminder_channel', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'owner_name': {'required': True}, 'scheduled_at': {'format': 'datetime', 'required': False}, 'appointment_type': {'allowed_values': ['wellness_exam', 'vaccination', 'surgery', 'dental', 'emergency', 'follow_up'], 'required': True}, 'veterinarian': {'required': False}, 'room': {'required': False}, 'duration_minutes': {'min': 5, 'max': 480, 'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}, 'notes': {'required': False}}
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
class BillingAndInvoicing:
    """Entity for capability billing_and_invoicing."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    owner_name: str = ""
    service_code: str = ""
    invoice_total: float = 0.0
    amount_paid: float = 0.0
    currency: str = 'USD'
    issued_on: str = '2026-09-03'
    due_on: str = '2026-09-03'
    payment_method: str = 'card'
    attachment_path: str = ""

    FIELDS = ['reference', 'status', 'owner_name', 'service_code', 'invoice_total', 'amount_paid', 'currency', 'issued_on', 'due_on', 'payment_method', 'attachment_path']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'owner_name': {'required': True}, 'service_code': {'required': True}, 'invoice_total': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'amount_paid': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'currency': {'allowed_values': ['USD', 'EUR', 'GBP', 'CAD'], 'required': False}, 'issued_on': {'format': 'date', 'required': False}, 'due_on': {'format': 'date', 'required': False}, 'payment_method': {'allowed_values': ['card', 'cash', 'insurance', 'bank_transfer'], 'required': False}, 'attachment_path': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BillingAndInvoicing":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ClientCommunicationAndReminders:
    """Entity for capability client_communication_and_reminders."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    owner_name: str = ""
    owner_email: str = ""
    reminder_type: str = 'appointment_reminder'
    channel: str = 'email'
    scheduled_for: str = '2026-09-03T10:00:00'
    template_name: str = ""
    message_body: str = ""

    FIELDS = ['reference', 'status', 'owner_name', 'owner_email', 'reminder_type', 'channel', 'scheduled_for', 'template_name', 'message_body']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'owner_name': {'required': True}, 'owner_email': {'format': 'email', 'required': False}, 'reminder_type': {'allowed_values': ['appointment_reminder', 'vaccination_reminder', 'follow_up', 'billing_notice'], 'required': True}, 'channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}, 'scheduled_for': {'format': 'datetime', 'required': False}, 'template_name': {'required': False}, 'message_body': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientCommunicationAndReminders":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ClinicalVisitNotesAndTreatmentPlans:
    """Entity for capability clinical_visit_notes_and_treatment_plans."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    visit_date: str = '2026-09-03'
    diagnosis: str = ""
    treatment_plan: str = ""
    medication: str = ""
    dosage_mg: float = 0.0
    administration_route: str = 'oral'
    attachment_path: str = ""
    prescription_notes: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'visit_date', 'diagnosis', 'treatment_plan', 'medication', 'dosage_mg', 'administration_route', 'attachment_path', 'prescription_notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'visit_date': {'format': 'date', 'required': False}, 'diagnosis': {'required': True}, 'treatment_plan': {'required': False}, 'medication': {'required': False}, 'dosage_mg': {'min': 0.0, 'max': 100000.0, 'required': False}, 'administration_route': {'allowed_values': ['oral', 'subcutaneous', 'intramuscular', 'intravenous', 'topical'], 'required': False}, 'attachment_path': {'required': False}, 'prescription_notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClinicalVisitNotesAndTreatmentPlans":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ComplianceAndAuditTrail:
    """Entity for capability compliance_and_audit_trail."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    record_type: str = 'clinical_note'
    subject_ref: str = ""
    content: str = ""
    content_hash: str = ""
    reviewer: str = ""
    reviewed_on: str = '2026-09-03'
    retention_until: str = '2026-09-03'

    FIELDS = ['reference', 'status', 'record_type', 'subject_ref', 'content', 'content_hash', 'reviewer', 'reviewed_on', 'retention_until']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'record_type': {'allowed_values': ['clinical_note', 'invoice', 'vaccination', 'consent_form'], 'required': True}, 'subject_ref': {'required': True}, 'content': {'required': True}, 'content_hash': {'required': False}, 'reviewer': {'required': False}, 'reviewed_on': {'format': 'date', 'required': False}, 'retention_until': {'format': 'date', 'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplianceAndAuditTrail":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class PatientAndOwnerRecords:
    """Entity for capability patient_and_owner_records."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    species: str = 'dog'
    breed: str = ""
    sex: str = 'male'
    age_years: int = 0
    weight_kg: float = 0.0
    microchip_id: str = ""
    owner_name: str = ""
    owner_email: str = ""
    owner_phone: str = ""
    clinical_history: str = ""

    FIELDS = ['reference', 'status', 'patient_name', 'species', 'breed', 'sex', 'age_years', 'weight_kg', 'microchip_id', 'owner_name', 'owner_email', 'owner_phone', 'clinical_history']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'species': {'allowed_values': ['dog', 'cat', 'rabbit', 'bird', 'reptile', 'other'], 'required': True}, 'breed': {'required': False}, 'sex': {'allowed_values': ['male', 'female', 'unknown'], 'required': False}, 'age_years': {'min': 0, 'max': 60, 'required': False}, 'weight_kg': {'min': 0.0, 'max': 300.0, 'required': False}, 'microchip_id': {'required': False}, 'owner_name': {'required': True}, 'owner_email': {'format': 'email', 'required': False}, 'owner_phone': {'required': False}, 'clinical_history': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatientAndOwnerRecords":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class VaccinationTracking:
    """Entity for capability vaccination_tracking."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    patient_name: str = ""
    vaccine_type: str = 'rabies'
    administered_on: str = '2026-09-03'
    next_due_on: str = '2026-09-03'
    lot_number: str = ""
    administered_by: str = ""
    reminder_channel: str = 'email'

    FIELDS = ['reference', 'status', 'patient_name', 'vaccine_type', 'administered_on', 'next_due_on', 'lot_number', 'administered_by', 'reminder_channel']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'patient_name': {'required': True}, 'vaccine_type': {'allowed_values': ['rabies', 'distemper', 'parvovirus', 'leptospirosis', 'bordetella', 'feline_herpesvirus', 'feline_calicivirus'], 'required': True}, 'administered_on': {'format': 'date', 'required': False}, 'next_due_on': {'format': 'date', 'required': False}, 'lot_number': {'required': False}, 'administered_by': {'required': False}, 'reminder_channel': {'allowed_values': ['email', 'sms', 'phone'], 'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VaccinationTracking":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {
    "analytics_and_reporting": AnalyticsAndReporting,
    "appointment_scheduling": AppointmentScheduling,
    "billing_and_invoicing": BillingAndInvoicing,
    "client_communication_and_reminders": ClientCommunicationAndReminders,
    "clinical_visit_notes_and_treatment_plans": ClinicalVisitNotesAndTreatmentPlans,
    "compliance_and_audit_trail": ComplianceAndAuditTrail,
    "patient_and_owner_records": PatientAndOwnerRecords,
    "vaccination_tracking": VaccinationTracking,
}
