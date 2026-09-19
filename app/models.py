"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class BranchOperations:
    """Entity for capability branch_and_consolidated_operations."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    branch: str = ""
    role_view: str = ""
    view_scope: str = ""
    period: str = ""
    metrics_summary: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'branch', 'role_view', 'view_scope', 'period', 'metrics_summary', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'branch': {'required': True}, 'role_view': {'required': True}, 'view_scope': {'required': False}, 'period': {'required': False}, 'metrics_summary': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BranchOperations":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class BookEntry:
    """Entity for capability branch_books_and_accounting."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    branch: str = ""
    entry_type: str = 'sale'
    entry_date: str = '2026-09-03'
    amount: float = 0
    margin_percent: float = 0
    ingredient: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'branch', 'entry_type', 'entry_date', 'amount', 'margin_percent', 'ingredient', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'branch': {'required': True}, 'entry_type': {'allowed_values': ['sale', 'cost', 'expense', 'taking', 'price_list'], 'required': True}, 'entry_date': {'required': False}, 'amount': {'min': 0, 'required': False}, 'margin_percent': {'min': 0, 'required': False}, 'ingredient': {'required': False}, 'notes': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookEntry":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class DeliveryRun:
    """Entity for capability delivery_and_dispatch."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    branch: str = ""
    driver: str = ""
    vehicle_type: str = 'car'
    vehicle_code: str = ""
    delivery_zone: str = ""
    route: str = ""
    order_reference: str = ""
    proof_of_delivery: str = ""
    scheduled_at: str = '2026-09-03T10:00:00'

    FIELDS = ['reference', 'status', 'branch', 'driver', 'vehicle_type', 'vehicle_code', 'delivery_zone', 'route', 'order_reference', 'proof_of_delivery', 'scheduled_at']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'branch': {'required': True}, 'driver': {'required': True}, 'vehicle_type': {'allowed_values': ['car', 'bike'], 'required': True}, 'vehicle_code': {'required': False}, 'delivery_zone': {'required': False}, 'route': {'required': False}, 'order_reference': {'required': False}, 'proof_of_delivery': {'required': False}, 'scheduled_at': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeliveryRun":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class KnowledgeQuery:
    """Entity for capability document_grounded_knowledge."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    branch: str = ""
    question: str = ""
    document_type: str = 'price_list'
    answer: str = ""
    citations: str = ""
    confidence: float = 0

    FIELDS = ['reference', 'status', 'branch', 'question', 'document_type', 'answer', 'citations', 'confidence']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'branch': {'required': True}, 'question': {'required': True}, 'document_type': {'allowed_values': ['price_list', 'recipe', 'ingredient_cost', 'delivery_zone', 'supplier_list', 'procedure'], 'required': True}, 'answer': {'required': False}, 'citations': {'required': False}, 'confidence': {'min': 0, 'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeQuery":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class EventOrder:
    """Entity for capability events_supply."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    branch: str = ""
    event_name: str = ""
    event_date: str = '2026-09-03'
    guest_count: int = 1
    deposit_amount: float = 0
    delivery_time: str = '10:00:00'
    venue: str = ""
    contact_email: str = ""

    FIELDS = ['reference', 'status', 'branch', 'event_name', 'event_date', 'guest_count', 'deposit_amount', 'delivery_time', 'venue', 'contact_email']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'branch': {'required': True}, 'event_name': {'required': True}, 'event_date': {'required': False}, 'guest_count': {'min': 1, 'required': False}, 'deposit_amount': {'min': 0, 'required': False}, 'delivery_time': {'required': False}, 'venue': {'required': False}, 'contact_email': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventOrder":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class InventoryItem:
    """Entity for capability inventory_and_replenishment."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    branch: str = ""
    item_name: str = ""
    item_type: str = 'ingredient'
    quantity_on_hand: int = 0
    reorder_threshold: int = 0
    unit: str = ""
    supplier: str = ""
    transfer_to_branch: str = ""
    low_stock: bool = False

    FIELDS = ['reference', 'status', 'branch', 'item_name', 'item_type', 'quantity_on_hand', 'reorder_threshold', 'unit', 'supplier', 'transfer_to_branch', 'low_stock']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'branch': {'required': True}, 'item_name': {'required': True}, 'item_type': {'allowed_values': ['ingredient', 'finished_good'], 'required': True}, 'quantity_on_hand': {'min': 0, 'required': False}, 'reorder_threshold': {'min': 0, 'required': False}, 'unit': {'required': False}, 'supplier': {'required': False}, 'transfer_to_branch': {'required': False}, 'low_stock': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventoryItem":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class OrderRecord:
    """Entity for capability order_follow_up."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    branch: str = ""
    channel: str = 'email'
    customer_name: str = ""
    order_status: str = ""
    payment_status: str = 'unpaid'
    confirmed: bool = False
    due_at: str = '2026-09-03T10:00:00'
    follow_up_note: str = ""

    FIELDS = ['reference', 'status', 'branch', 'channel', 'customer_name', 'order_status', 'payment_status', 'confirmed', 'due_at', 'follow_up_note']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'branch': {'required': True}, 'channel': {'allowed_values': ['email', 'phone', 'counter', 'outlook'], 'required': True}, 'customer_name': {'required': True}, 'order_status': {'required': False}, 'payment_status': {'allowed_values': ['unpaid', 'paid', 'partial'], 'required': False}, 'confirmed': {'required': False}, 'due_at': {'required': False}, 'follow_up_note': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderRecord":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class OutlookMessage:
    """Entity for capability outlook_branch_messaging_integration."""

    id: Optional[int] = None
    reference: str = ""
    status: str = 'open'
    branch: str = ""
    mailbox: str = ""
    direction: str = 'inbound'
    subject: str = ""
    body: str = ""
    message_reference: str = ""
    received_at: str = '2026-09-03T10:00:00'

    FIELDS = ['reference', 'status', 'branch', 'mailbox', 'direction', 'subject', 'body', 'message_reference', 'received_at']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'branch': {'required': True}, 'mailbox': {'required': True}, 'direction': {'allowed_values': ['inbound', 'outbound'], 'required': True}, 'subject': {'required': False}, 'body': {'required': False}, 'message_reference': {'required': False}, 'received_at': {'required': False}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutlookMessage":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {
    "branch_and_consolidated_operations": BranchOperations,
    "branch_books_and_accounting": BookEntry,
    "delivery_and_dispatch": DeliveryRun,
    "document_grounded_knowledge": KnowledgeQuery,
    "events_supply": EventOrder,
    "inventory_and_replenishment": InventoryItem,
    "order_follow_up": OrderRecord,
    "outlook_branch_messaging_integration": OutlookMessage,
}
