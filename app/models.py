"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class DocumentAndKnowledgeAnswers:
    """Entity for capability document_and_knowledge_answers."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    title: str = ""
    document_kind: str = 'manual'
    question: str = ""
    document_text: str = ""
    attachment_path: str = ""
    answer: str = ""
    source_document: str = ""
    authority_label: str = 'certified'
    notes: str = ""

    FIELDS = ['reference', 'status', 'title', 'document_kind', 'question', 'document_text', 'attachment_path', 'answer', 'source_document', 'authority_label', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'title': {'required': True}, 'document_kind': {'allowed_values': ['manual', 'sop', 'rate_sheet', 'policy', 'other'], 'required': True}, 'question': {'required': True}, 'document_text': {'required': True}, 'attachment_path': {'required': False}, 'answer': {'required': False}, 'source_document': {'required': False}, 'authority_label': {'allowed_values': ['certified', 'documents', 'formulas', 'procedures'], 'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentAndKnowledgeAnswers":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ExternalIntegrationAdapter:
    """Entity for capability external_integration_adapter."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    system: str = 'opera'
    resource: str = ""
    direction: str = 'inbound'
    payload_format: str = 'json'
    endpoint_url: str = ""
    records_seen: int = 0
    notes: str = ""

    FIELDS = ['reference', 'status', 'system', 'resource', 'direction', 'payload_format', 'endpoint_url', 'records_seen', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'system': {'allowed_values': ['opera', 'micros', 'maximo', 'loyalty_lms', 'grms', 'gaming_cms'], 'required': True}, 'resource': {'required': True}, 'direction': {'allowed_values': ['inbound', 'outbound'], 'required': True}, 'payload_format': {'allowed_values': ['json', 'csv', 'xml'], 'required': True}, 'endpoint_url': {'required': False}, 'records_seen': {'min': 0, 'required': False, 'type': 'int'}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExternalIntegrationAdapter":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class FrontDeskAndGuestStay:
    """Entity for capability front_desk_and_guest_stay."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    guest_name: str = ""
    room_number: str = ""
    arrival_date: str = '2026-09-03'
    departure_date: str = '2026-09-03'
    guests_count: int = 1
    stay_status: str = 'reserved'
    folio_currency: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'guest_name', 'room_number', 'arrival_date', 'departure_date', 'guests_count', 'stay_status', 'folio_currency', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': True}, 'arrival_date': {'required': True}, 'departure_date': {'required': False}, 'guests_count': {'min': 1, 'max': 10, 'required': False, 'type': 'int'}, 'stay_status': {'allowed_values': ['reserved', 'checked_in', 'checked_out', 'no_show', 'cancelled'], 'required': True}, 'folio_currency': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FrontDeskAndGuestStay":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class GuestEngagementAndSegmentation:
    """Entity for capability guest_engagement_and_segmentation."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    guest_name: str = ""
    recency_days: int = 0
    frequency: int = 0
    monetary: float = 0.0
    segment: str = 'champion'
    delivery_channel: str = 'mcp'
    offer_code: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'guest_name', 'recency_days', 'frequency', 'monetary', 'segment', 'delivery_channel', 'offer_code', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'guest_name': {'required': True}, 'recency_days': {'min': 0, 'max': 3650, 'required': True, 'type': 'int'}, 'frequency': {'min': 0, 'max': 1000, 'required': True, 'type': 'int'}, 'monetary': {'min': 0.0, 'max': 1000000.0, 'required': True, 'type': 'float'}, 'segment': {'allowed_values': ['champion', 'loyal', 'potential', 'at_risk', 'dormant'], 'required': False}, 'delivery_channel': {'allowed_values': ['mcp', 'email'], 'required': True}, 'offer_code': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuestEngagementAndSegmentation":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class HousekeepingAndMaintenance:
    """Entity for capability housekeeping_and_maintenance."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    title: str = ""
    work_type: str = 'housekeeping'
    room_number: str = ""
    priority: str = 'low'
    due_date: str = '2026-09-03'
    assigned_to: str = ""
    work_status: str = 'open'
    notes: str = ""

    FIELDS = ['reference', 'status', 'title', 'work_type', 'room_number', 'priority', 'due_date', 'assigned_to', 'work_status', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'title': {'required': True}, 'work_type': {'allowed_values': ['housekeeping', 'maintenance', 'inspection'], 'required': True}, 'room_number': {'required': True}, 'priority': {'allowed_values': ['low', 'normal', 'high', 'urgent'], 'required': True}, 'due_date': {'required': False}, 'assigned_to': {'required': False}, 'work_status': {'allowed_values': ['open', 'assigned', 'in_progress', 'done', 'cancelled'], 'required': True}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HousekeepingAndMaintenance":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class OperationsBilling:
    """Entity for capability operations_billing."""

    id: Optional[int] = None
    setting: str = ""
    reference: str = ""
    status: str = 'open'
    folio_reference: str = ""
    charge_type: str = 'room'
    amount: float = 0.0
    currency: str = ""
    tax_rate_percent: float = 0.0
    total_amount: float = 0.0
    notes: str = ""

    FIELDS = ['setting', 'reference', 'status', 'folio_reference', 'charge_type', 'amount', 'currency', 'tax_rate_percent', 'total_amount', 'notes']
    CONSTRAINTS = {'setting': {'required': True}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'folio_reference': {'required': True}, 'charge_type': {'allowed_values': ['room', 'food_and_beverage', 'spa', 'minibar', 'laundry', 'other'], 'required': True}, 'amount': {'min': 0.0, 'max': 1000000.0, 'required': True, 'type': 'float'}, 'currency': {'required': False}, 'tax_rate_percent': {'min': 0.0, 'max': 100.0, 'required': False, 'type': 'float'}, 'total_amount': {'min': 0.0, 'required': False, 'type': 'float'}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationsBilling":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class OperationsOversightDashboard:
    """Entity for capability operations_oversight_dashboard."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    dashboard_name: str = ""
    widget: str = 'occupancy'
    window_days: int = 1
    operator_role: str = 'operator'
    occupancy_percent: float = 0.0
    open_work_orders: int = 0
    notes: str = ""

    FIELDS = ['reference', 'status', 'dashboard_name', 'widget', 'window_days', 'operator_role', 'occupancy_percent', 'open_work_orders', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'dashboard_name': {'required': True}, 'widget': {'allowed_values': ['occupancy', 'room_status', 'work_orders', 'guest_activity'], 'required': True}, 'window_days': {'min': 1, 'max': 90, 'required': False, 'type': 'int'}, 'operator_role': {'allowed_values': ['operator', 'admin'], 'required': True}, 'occupancy_percent': {'min': 0.0, 'max': 100.0, 'required': False, 'type': 'float'}, 'open_work_orders': {'min': 0, 'max': 10000, 'required': False, 'type': 'int'}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationsOversightDashboard":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class PropertyAndRoomRegistry:
    """Entity for capability property_and_room_registry."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    property_name: str = ""
    building: str = ""
    floor: int = 0
    room_number: str = ""
    room_type: str = 'standard'
    capacity: int = 1
    room_status: str = 'available'
    notes: str = ""

    FIELDS = ['reference', 'status', 'property_name', 'building', 'floor', 'room_number', 'room_type', 'capacity', 'room_status', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'property_name': {'required': True}, 'building': {'required': False}, 'floor': {'min': 0, 'max': 200, 'required': False, 'type': 'int'}, 'room_number': {'required': True}, 'room_type': {'allowed_values': ['standard', 'superior', 'deluxe', 'suite', 'accessible'], 'required': True}, 'capacity': {'min': 1, 'max': 12, 'required': False, 'type': 'int'}, 'room_status': {'allowed_values': ['available', 'occupied', 'dirty', 'cleaned', 'out_of_order'], 'required': True}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PropertyAndRoomRegistry":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {
    "document_and_knowledge_answers": DocumentAndKnowledgeAnswers,
    "external_integration_adapter": ExternalIntegrationAdapter,
    "front_desk_and_guest_stay": FrontDeskAndGuestStay,
    "guest_engagement_and_segmentation": GuestEngagementAndSegmentation,
    "housekeeping_and_maintenance": HousekeepingAndMaintenance,
    "operations_billing": OperationsBilling,
    "operations_oversight_dashboard": OperationsOversightDashboard,
    "property_and_room_registry": PropertyAndRoomRegistry,
}
