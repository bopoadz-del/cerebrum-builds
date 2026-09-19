"""Domain models for the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

Plain dataclasses on purpose: the delivered platform must run with no ORM, no
service and no network. Persistence lives in ``app/store.py``; the schema is
applied by Alembic (``alembic/versions/0001_baseline.py``).

Envelope vocabulary is schema-enforced, not prose: every capability carries a
``status`` column whose ``allowed_values`` are exactly
``open | in_progress | closed`` and the HTTP route rejects anything else with
HTTP 422 before a handler is called.

One user is one tenant; the shop/driver records below are the chain's own data.

Scope
-----
READS  nothing.
WRITES nothing.
NEVER  network, ``vendor/**``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

ENVELOPE_STATUS_VALUES = ("open", "in_progress", "closed")


def _envelope_status() -> Dict[str, Any]:
    return {"required": True, "allowed_values": list(ENVELOPE_STATUS_VALUES)}


@dataclass
class StockInventoryManagement:
    """Entity for capability stock_inventory_management."""

    id: Optional[int] = None
    reference: str = ""
    shop_code: str = ""
    item_code: str = ""
    item_name: str = ""
    quantity_on_hand: int = 0
    reorder_threshold: int = 0
    unit: str = ""
    movement_type: str = ""
    notes: str = ""
    status: str = ""

    FIELDS = ['reference', 'shop_code', 'item_code', 'item_name', 'quantity_on_hand', 'reorder_threshold', 'unit', 'movement_type', 'notes', 'status']
    CONSTRAINTS = {
        "reference": {"required": True},
        "shop_code": {"required": True},
        "item_code": {"required": True},
        "item_name": {"required": True},
        "quantity_on_hand": {"required": True, "min": 0},
        "reorder_threshold": {"required": True, "min": 0},
        "unit": {"required": True},
        "movement_type": {"required": True, "allowed_values": ['receipt', 'issue', 'waste', 'transfer', 'adjustment']},
        "notes": {},
        "status": {"required": True, "allowed_values": ['open', 'in_progress', 'closed']},
    }
    ENTITY = 'stock_inventory_management'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockInventoryManagement":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class DeliveryDispatchTracking:
    """Entity for capability delivery_dispatch_tracking."""

    id: Optional[int] = None
    reference: str = ""
    order_code: str = ""
    shop_code: str = ""
    driver_code: str = ""
    vehicle_code: str = ""
    vehicle_type: str = ""
    delivery_address: str = ""
    scheduled_at: str = ""
    delivery_state: str = ""
    notes: str = ""
    status: str = ""

    FIELDS = ['reference', 'order_code', 'shop_code', 'driver_code', 'vehicle_code', 'vehicle_type', 'delivery_address', 'scheduled_at', 'delivery_state', 'notes', 'status']
    CONSTRAINTS = {
        "reference": {"required": True},
        "order_code": {"required": True},
        "shop_code": {"required": True},
        "driver_code": {"required": True},
        "vehicle_code": {"required": True},
        "vehicle_type": {"required": True, "allowed_values": ['bike', 'car']},
        "delivery_address": {"required": True},
        "scheduled_at": {"required": True, "format": 'datetime'},
        "delivery_state": {"required": True, "allowed_values": ['pending', 'assigned', 'picked_up', 'delivered', 'failed']},
        "notes": {},
        "status": {"required": True, "allowed_values": ['open', 'in_progress', 'closed']},
    }
    ENTITY = 'delivery_dispatch_tracking'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeliveryDispatchTracking":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class DocumentKnowledgeQa:
    """Entity for capability document_knowledge_qa."""

    id: Optional[int] = None
    reference: str = ""
    document_title: str = ""
    document_type: str = ""
    source_path: str = ""
    question: str = ""
    answer: str = ""
    notes: str = ""
    status: str = ""

    FIELDS = ['reference', 'document_title', 'document_type', 'source_path', 'question', 'answer', 'notes', 'status']
    CONSTRAINTS = {
        "reference": {"required": True},
        "document_title": {"required": True},
        "document_type": {"required": True, "allowed_values": ['unit_prices', 'operating_procedure', 'other']},
        "source_path": {},
        "question": {"required": True},
        "answer": {},
        "notes": {},
        "status": {"required": True, "allowed_values": ['open', 'in_progress', 'closed']},
    }
    ENTITY = 'document_knowledge_qa'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentKnowledgeQa":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class FleetCostAndPricing:
    """Entity for capability fleet_cost_and_pricing."""

    id: Optional[int] = None
    reference: str = ""
    vehicle_code: str = ""
    vehicle_type: str = ""
    distance_km: float = 0.0
    unit_price: float = 0.0
    operating_cost: float = 0.0
    price_basis: str = ""
    notes: str = ""
    status: str = ""

    FIELDS = ['reference', 'vehicle_code', 'vehicle_type', 'distance_km', 'unit_price', 'operating_cost', 'price_basis', 'notes', 'status']
    CONSTRAINTS = {
        "reference": {"required": True},
        "vehicle_code": {"required": True},
        "vehicle_type": {"required": True, "allowed_values": ['bike', 'car']},
        "distance_km": {"required": True, "min": 0},
        "unit_price": {"required": True, "min": 0},
        "operating_cost": {"min": 0},
        "price_basis": {"required": True},
        "notes": {},
        "status": {"required": True, "allowed_values": ['open', 'in_progress', 'closed']},
    }
    ENTITY = 'fleet_cost_and_pricing'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FleetCostAndPricing":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ManagementReportingDashboard:
    """Entity for capability management_reporting_dashboard."""

    id: Optional[int] = None
    reference: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    shop_code: str = ""
    reporting_period: str = ""
    notes: str = ""
    status: str = ""

    FIELDS = ['reference', 'metric_name', 'metric_value', 'shop_code', 'reporting_period', 'notes', 'status']
    CONSTRAINTS = {
        "reference": {"required": True},
        "metric_name": {"required": True},
        "metric_value": {"required": True, "min": 0},
        "shop_code": {"required": True},
        "reporting_period": {"required": True},
        "notes": {},
        "status": {"required": True, "allowed_values": ['open', 'in_progress', 'closed']},
    }
    ENTITY = 'management_reporting_dashboard'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManagementReportingDashboard":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class UserRolesWorkforce:
    """Entity for capability user_roles_workforce."""

    id: Optional[int] = None
    reference: str = ""
    user_name: str = ""
    user_email: str = ""
    role: str = ""
    shop_code: str = ""
    shift: str = ""
    notes: str = ""
    status: str = ""

    FIELDS = ['reference', 'user_name', 'user_email', 'role', 'shop_code', 'shift', 'notes', 'status']
    CONSTRAINTS = {
        "reference": {"required": True},
        "user_name": {"required": True},
        "user_email": {"required": True},
        "role": {"required": True, "allowed_values": ['operator', 'admin', 'driver', 'shop_user']},
        "shop_code": {"required": True},
        "shift": {"required": True, "allowed_values": ['morning', 'afternoon', 'night']},
        "notes": {},
        "status": {"required": True, "allowed_values": ['open', 'in_progress', 'closed']},
    }
    ENTITY = 'user_roles_workforce'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserRolesWorkforce":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class OperationalProceduresReadiness:
    """Entity for capability operational_procedures_readiness."""

    id: Optional[int] = None
    reference: str = ""
    procedure_code: str = ""
    procedure_title: str = ""
    shop_code: str = ""
    checklist: str = ""
    due_date: str = ""
    notes: str = ""
    status: str = ""

    FIELDS = ['reference', 'procedure_code', 'procedure_title', 'shop_code', 'checklist', 'due_date', 'notes', 'status']
    CONSTRAINTS = {
        "reference": {"required": True},
        "procedure_code": {"required": True},
        "procedure_title": {"required": True},
        "shop_code": {"required": True},
        "checklist": {"required": True},
        "due_date": {"format": 'date'},
        "notes": {},
        "status": {"required": True, "allowed_values": ['open', 'in_progress', 'closed']},
    }
    ENTITY = 'operational_procedures_readiness'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationalProceduresReadiness":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class AuditEvidenceTrail:
    """Entity for capability audit_evidence_trail."""

    id: Optional[int] = None
    reference: str = ""
    event_type: str = ""
    entity_name: str = ""
    actor: str = ""
    evidence_path: str = ""
    content_hash: str = ""
    notes: str = ""
    status: str = ""

    FIELDS = ['reference', 'event_type', 'entity_name', 'actor', 'evidence_path', 'content_hash', 'notes', 'status']
    CONSTRAINTS = {
        "reference": {"required": True},
        "event_type": {"required": True},
        "entity_name": {"required": True},
        "actor": {"required": True},
        "evidence_path": {},
        "content_hash": {},
        "notes": {},
        "status": {"required": True, "allowed_values": ['open', 'in_progress', 'closed']},
    }
    ENTITY = 'audit_evidence_trail'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvidenceTrail":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)

MODELS = {
    "stock_inventory_management": StockInventoryManagement,
    "delivery_dispatch_tracking": DeliveryDispatchTracking,
    "document_knowledge_qa": DocumentKnowledgeQa,
    "fleet_cost_and_pricing": FleetCostAndPricing,
    "management_reporting_dashboard": ManagementReportingDashboard,
    "user_roles_workforce": UserRolesWorkforce,
    "operational_procedures_readiness": OperationalProceduresReadiness,
    "audit_evidence_trail": AuditEvidenceTrail,
}

#: capability_id -> persist entity (alembic 0001 table + store.COLUMNS).
ENTITIES = {cid: cls.ENTITY for cid, cls in MODELS.items()}
