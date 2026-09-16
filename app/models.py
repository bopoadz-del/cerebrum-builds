"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class InventoryManagement:
    """Entity for capability inventory_management."""

    id: Optional[int] = None
    reference: str = ""
    status: str = ""
    sku: str = ""
    product_name: str = ""
    location: str = ""
    quantity_on_hand: int = 0
    reorder_point: int = 0
    unit_cost: float = 0.0
    supplier_name: str = ""
    category: str = ""
    movement_type: str = ""
    last_counted_date: str = '2026-09-03'

    FIELDS = ['reference', 'status', 'sku', 'product_name', 'location', 'quantity_on_hand', 'reorder_point', 'unit_cost', 'supplier_name', 'category', 'movement_type', 'last_counted_date']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'sku': {'required': True}, 'product_name': {'required': True}, 'location': {'required': False}, 'quantity_on_hand': {'min': 0, 'max': 100000, 'required': False}, 'reorder_point': {'min': 0, 'max': 100000, 'required': False}, 'unit_cost': {'min': 0.0, 'max': 100000.0, 'required': False}, 'supplier_name': {'required': False}, 'category': {'required': False}, 'movement_type': {'required': False}, 'last_counted_date': {'format': 'date', 'required': False}}
    ENTITY = 'inventory_management'
    CAPABILITY_ID = 'inventory_management'
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
class SalesAndOrders:
    """Entity for capability sales_and_orders."""

    id: Optional[int] = None
    reference: str = ""
    status: str = ""
    order_number: str = ""
    customer_name: str = ""
    customer_email: str = ""
    channel: str = ""
    order_total: float = 0.0
    item_count: int = 0
    payment_status: str = ""
    fulfilment_status: str = ""
    order_date: str = '2026-09-03'
    notes: str = ""

    FIELDS = ['reference', 'status', 'order_number', 'customer_name', 'customer_email', 'channel', 'order_total', 'item_count', 'payment_status', 'fulfilment_status', 'order_date', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'order_number': {'required': True}, 'customer_name': {'required': True}, 'customer_email': {'required': False}, 'channel': {'required': False}, 'order_total': {'min': 0.0, 'max': 1000000.0, 'required': False}, 'item_count': {'min': 0, 'max': 100000, 'required': False}, 'payment_status': {'required': False}, 'fulfilment_status': {'required': False}, 'order_date': {'format': 'date', 'required': False}, 'notes': {'required': False}}
    ENTITY = 'sales_and_orders'
    CAPABILITY_ID = 'sales_and_orders'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SalesAndOrders":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class CustomerInsights:
    """Entity for capability customer_insights."""

    id: Optional[int] = None
    reference: str = ""
    status: str = ""
    customer_name: str = ""
    customer_email: str = ""
    segment: str = ""
    lifetime_value: float = 0.0
    orders_count: int = 0
    last_purchase_date: str = '2026-09-03'
    loyalty_tier: str = ""
    preferred_channel: str = ""
    insight_summary: str = ""
    tags: str = ""

    FIELDS = ['reference', 'status', 'customer_name', 'customer_email', 'segment', 'lifetime_value', 'orders_count', 'last_purchase_date', 'loyalty_tier', 'preferred_channel', 'insight_summary', 'tags']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'customer_name': {'required': True}, 'customer_email': {'required': False}, 'segment': {'required': False}, 'lifetime_value': {'min': 0.0, 'max': 10000000.0, 'required': False}, 'orders_count': {'min': 0, 'max': 1000000, 'required': False}, 'last_purchase_date': {'format': 'date', 'required': False}, 'loyalty_tier': {'required': False}, 'preferred_channel': {'required': False}, 'insight_summary': {'required': False}, 'tags': {'required': False}}
    ENTITY = 'customer_insights'
    CAPABILITY_ID = 'customer_insights'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomerInsights":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class AnalyticsDashboard:
    """Entity for capability analytics_dashboard."""

    id: Optional[int] = None
    reference: str = ""
    status: str = ""
    dashboard_name: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    period_start: str = '2026-09-03'
    period_end: str = '2026-09-03'
    store_location: str = ""
    widget_type: str = ""
    report_format: str = ""
    owner: str = ""
    generated_at: str = '2026-09-03T10:00:00'

    FIELDS = ['reference', 'status', 'dashboard_name', 'metric_name', 'metric_value', 'period_start', 'period_end', 'store_location', 'widget_type', 'report_format', 'owner', 'generated_at']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'dashboard_name': {'required': True}, 'metric_name': {'required': True}, 'metric_value': {'min': 0.0, 'max': 100000000.0, 'required': False}, 'period_start': {'format': 'date', 'required': False}, 'period_end': {'format': 'date', 'required': False}, 'store_location': {'required': False}, 'widget_type': {'required': False}, 'report_format': {'required': False}, 'owner': {'required': False}, 'generated_at': {'format': 'datetime', 'required': False}}
    ENTITY = 'analytics_dashboard'
    CAPABILITY_ID = 'analytics_dashboard'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalyticsDashboard":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class SupplierAndPurchasing:
    """Entity for capability supplier_and_purchasing."""

    id: Optional[int] = None
    reference: str = ""
    status: str = ""
    supplier_name: str = ""
    supplier_email: str = ""
    purchase_order_number: str = ""
    sku: str = ""
    quantity_ordered: int = 0
    unit_cost: float = 0.0
    lead_time_days: int = 0
    order_date: str = '2026-09-03'
    expected_date: str = '2026-09-03'
    payment_terms: str = ""

    FIELDS = ['reference', 'status', 'supplier_name', 'supplier_email', 'purchase_order_number', 'sku', 'quantity_ordered', 'unit_cost', 'lead_time_days', 'order_date', 'expected_date', 'payment_terms']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'supplier_name': {'required': True}, 'supplier_email': {'required': False}, 'purchase_order_number': {'required': True}, 'sku': {'required': False}, 'quantity_ordered': {'min': 0, 'max': 100000, 'required': False}, 'unit_cost': {'min': 0.0, 'max': 100000.0, 'required': False}, 'lead_time_days': {'min': 0, 'max': 365, 'required': False}, 'order_date': {'format': 'date', 'required': False}, 'expected_date': {'format': 'date', 'required': False}, 'payment_terms': {'required': False}}
    ENTITY = 'supplier_and_purchasing'
    CAPABILITY_ID = 'supplier_and_purchasing'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SupplierAndPurchasing":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class OmnichannelIntegration:
    """Entity for capability omnichannel_integration."""

    id: Optional[int] = None
    reference: str = ""
    status: str = ""
    integration_name: str = ""
    channel: str = ""
    external_order_id: str = ""
    sync_direction: str = ""
    sync_status: str = ""
    sku: str = ""
    quantity: int = 0
    sync_at: str = '2026-09-03T10:00:00'
    marketplace: str = ""
    notes: str = ""

    FIELDS = ['reference', 'status', 'integration_name', 'channel', 'external_order_id', 'sync_direction', 'sync_status', 'sku', 'quantity', 'sync_at', 'marketplace', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'integration_name': {'required': True}, 'channel': {'required': False}, 'external_order_id': {'required': False}, 'sync_direction': {'required': False}, 'sync_status': {'required': False}, 'sku': {'required': False}, 'quantity': {'min': 0, 'max': 100000, 'required': False}, 'sync_at': {'format': 'datetime', 'required': False}, 'marketplace': {'required': False}, 'notes': {'required': False}}
    ENTITY = 'omnichannel_integration'
    CAPABILITY_ID = 'omnichannel_integration'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OmnichannelIntegration":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ComplianceAndAudit:
    """Entity for capability compliance_and_audit."""

    id: Optional[int] = None
    reference: str = ""
    status: str = ""
    control_id: str = ""
    regulation: str = ""
    event_type: str = ""
    actor: str = ""
    action_taken: str = ""
    evidence_ref: str = ""
    file_path: str = ""
    findings: str = ""
    occurred_at: str = '2026-09-03T10:00:00'
    severity: str = ""

    FIELDS = ['reference', 'status', 'control_id', 'regulation', 'event_type', 'actor', 'action_taken', 'evidence_ref', 'file_path', 'findings', 'occurred_at', 'severity']
    CONSTRAINTS = {'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'control_id': {'required': True}, 'regulation': {'required': False}, 'event_type': {'required': False}, 'actor': {'required': False}, 'action_taken': {'required': False}, 'evidence_ref': {'required': False}, 'file_path': {'required': False}, 'findings': {'required': False}, 'occurred_at': {'format': 'datetime', 'required': False}, 'severity': {'required': False}}
    ENTITY = 'compliance_and_audit'
    CAPABILITY_ID = 'compliance_and_audit'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplianceAndAudit":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {
    "inventory_management": InventoryManagement,
    "sales_and_orders": SalesAndOrders,
    "customer_insights": CustomerInsights,
    "analytics_dashboard": AnalyticsDashboard,
    "supplier_and_purchasing": SupplierAndPurchasing,
    "omnichannel_integration": OmnichannelIntegration,
    "compliance_and_audit": ComplianceAndAudit,
}

