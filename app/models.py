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
    pet_name: str = ""
    owner_name: str = ""
    veterinarian: str = ""
    appointment_date: str = '2026-09-03'
    appointment_time: str = '10:00:00'
    duration_minutes: int = 5
    visit_reason: str = ""
    room: str = ""
    appointment_status: str = ""

    FIELDS = ['reference', 'status', 'pet_name', 'owner_name', 'veterinarian', 'appointment_date', 'appointment_time', 'duration_minutes', 'visit_reason', 'room', 'appointment_status']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'pet_name': {'required': True}, 'owner_name': {'required': False}, 'veterinarian': {'required': True}, 'appointment_date': {'required': False}, 'appointment_time': {'required': False}, 'duration_minutes': {'min': 5, 'max': 480, 'required': False}, 'visit_reason': {'required': False}, 'room': {'required': False}, 'appointment_status': {'required': False}}
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
class AuditTrail:
    """Entity for capability audit_trail."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    event_type: str = ""
    entity_name: str = ""
    entity_id: str = ""
    actor: str = ""
    actor_role: str = ""
    action_taken: str = ""
    details: str = ""
    occurred_at: str = '2026-09-03T10:00:00'

    FIELDS = ['reference', 'status', 'event_type', 'entity_name', 'entity_id', 'actor', 'actor_role', 'action_taken', 'details', 'occurred_at']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'event_type': {'required': True}, 'entity_name': {'required': False}, 'entity_id': {'required': False}, 'actor': {'required': True}, 'actor_role': {'required': False}, 'action_taken': {'required': False}, 'details': {'required': False}, 'occurred_at': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditTrail":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class BillingInvoicing:
    """Entity for capability billing_invoicing."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    invoice_number: str = ""
    client_name: str = ""
    pet_name: str = ""
    line_items: str = ""
    subtotal: float = 0.0
    tax_rate: float = 0.0
    total_amount: float = 0.0
    payment_status: str = ""
    payment_method: str = ""
    invoice_date: str = '2026-09-03'
    attachment_path: str = ""

    FIELDS = ['reference', 'status', 'invoice_number', 'client_name', 'pet_name', 'line_items', 'subtotal', 'tax_rate', 'total_amount', 'payment_status', 'payment_method', 'invoice_date', 'attachment_path']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'invoice_number': {'required': True}, 'client_name': {'required': True}, 'pet_name': {'required': False}, 'line_items': {'required': False}, 'subtotal': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'tax_rate': {'min': 0.0, 'max': 1.0, 'required': False}, 'total_amount': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'payment_status': {'required': False}, 'payment_method': {'required': False}, 'invoice_date': {'required': False}, 'attachment_path': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BillingInvoicing":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ClinicAnalytics:
    """Entity for capability clinic_analytics."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    metric_name: str = ""
    metric_value: float = 0.0
    period: str = ""
    period_start: str = '2026-09-03'
    period_end: str = '2026-09-03'
    dimension: str = ""

    FIELDS = ['reference', 'status', 'metric_name', 'metric_value', 'period', 'period_start', 'period_end', 'dimension']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'metric_name': {'required': True}, 'metric_value': {'min': 0.0, 'max': 100000000.0, 'required': False}, 'period': {'required': False}, 'period_start': {'required': False}, 'period_end': {'required': False}, 'dimension': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClinicAnalytics":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class InventoryManagement:
    """Entity for capability inventory_management."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    item_name: str = ""
    sku: str = ""
    category: str = ""
    quantity: int = 0
    reorder_level: int = 0
    unit_cost: float = 0.0
    supplier: str = ""
    expiry_date: str = '2026-09-03'

    FIELDS = ['reference', 'status', 'item_name', 'sku', 'category', 'quantity', 'reorder_level', 'unit_cost', 'supplier', 'expiry_date']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'item_name': {'required': True}, 'sku': {'required': True}, 'category': {'required': False}, 'quantity': {'min': 0, 'max': 1000000, 'required': False}, 'reorder_level': {'min': 0, 'max': 100000, 'required': False}, 'unit_cost': {'min': 0.0, 'max': 100000.0, 'required': False}, 'supplier': {'required': False}, 'expiry_date': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventoryManagement":
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
    pet_name: str = ""
    species: str = ""
    breed: str = ""
    owner_name: str = ""
    owner_email: str = 'guest@example.com'
    owner_phone: str = ""
    date_of_birth: str = '2026-09-03'
    weight_kg: float = 0.0
    vaccination_status: str = ""
    allergies: str = ""
    clinical_notes: str = ""

    FIELDS = ['reference', 'status', 'pet_name', 'species', 'breed', 'owner_name', 'owner_email', 'owner_phone', 'date_of_birth', 'weight_kg', 'vaccination_status', 'allergies', 'clinical_notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'pet_name': {'required': True}, 'species': {'required': False}, 'breed': {'required': False}, 'owner_name': {'required': True}, 'owner_email': {'required': False}, 'owner_phone': {'required': False}, 'date_of_birth': {'required': False}, 'weight_kg': {'min': 0.0, 'max': 500.0, 'required': False}, 'vaccination_status': {'required': False}, 'allergies': {'required': False}, 'clinical_notes': {'required': False}}
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
class RoleManagement:
    """Entity for capability role_management."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    role_name: str = ""
    display_name: str = ""
    permissions: str = ""
    access_level: str = ""
    department: str = ""
    is_active: bool = False

    FIELDS = ['reference', 'status', 'role_name', 'display_name', 'permissions', 'access_level', 'department', 'is_active']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'role_name': {'required': True}, 'display_name': {'required': False}, 'permissions': {'required': False}, 'access_level': {'required': False}, 'department': {'required': False}, 'is_active': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoleManagement":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class TreatmentManagement:
    """Entity for capability treatment_management."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    pet_name: str = ""
    veterinarian: str = ""
    treatment_type: str = ""
    diagnosis: str = ""
    procedure_notes: str = ""
    medication: str = ""
    dosage: str = ""
    treatment_date: str = '2026-09-03'
    follow_up_date: str = '2026-09-03'
    attachment_path: str = ""

    FIELDS = ['reference', 'status', 'pet_name', 'veterinarian', 'treatment_type', 'diagnosis', 'procedure_notes', 'medication', 'dosage', 'treatment_date', 'follow_up_date', 'attachment_path']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'pet_name': {'required': True}, 'veterinarian': {'required': True}, 'treatment_type': {'required': False}, 'diagnosis': {'required': False}, 'procedure_notes': {'required': False}, 'medication': {'required': False}, 'dosage': {'required': False}, 'treatment_date': {'required': False}, 'follow_up_date': {'required': False}, 'attachment_path': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreatmentManagement":
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
    "audit_trail": AuditTrail,
    "billing_invoicing": BillingInvoicing,
    "clinic_analytics": ClinicAnalytics,
    "inventory_management": InventoryManagement,
    "patient_records": PatientRecords,
    "role_management": RoleManagement,
    "treatment_management": TreatmentManagement,
}
