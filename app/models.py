"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AuditTrail:
    """Entity for capability audit_trail."""

    id: Optional[int] = None
    action_kind: str = ""
    actor: str = ""
    target: str = ""
    detail: str = ""
    content: str = ""
    attachment_path: str = ""
    reference: str = ""
    status: str = 'open'

    audit: str = ""
    capture: str = ""
    evidence_verifier: str = ""
    file_hasher: str = ""
    FIELDS = ['action_kind', 'actor', 'target', 'detail', 'content', 'attachment_path', 'reference', 'status', 'audit', 'capture', 'evidence_verifier', 'file_hasher']
    CONSTRAINTS = {'audit': {'required': True}, 'capture': {'required': True}, 'evidence_verifier': {'required': True}, 'file_hasher': {'required': True}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
class FleetRegistry:
    """Entity for capability fleet_registry."""

    id: Optional[int] = None
    plate_number: str = ""
    vin: str = ""
    branch: str = ""
    category: str = ""
    vehicle_state: str = ""
    mileage: int = 0
    service_history: str = ""
    attachment_path: str = ""
    reference: str = ""
    status: str = 'open'

    audit: str = ""
    database: str = ""
    storage: str = ""
    FIELDS = ['plate_number', 'vin', 'branch', 'category', 'vehicle_state', 'mileage', 'service_history', 'attachment_path', 'reference', 'status', 'audit', 'database', 'storage']
    CONSTRAINTS = {'audit': {'required': True}, 'database': {'required': True}, 'storage': {'required': True}, 'mileage': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FleetRegistry":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class InvoicingAndDeposits:
    """Entity for capability invoicing_and_deposits."""

    id: Optional[int] = None
    invoice_number: str = ""
    contract_reference: str = ""
    branch: str = ""
    amount_due: float = 0
    deposit_held: float = 0
    credit_note: str = ""
    balance_due: float = 0
    reference: str = ""
    status: str = 'open'

    analytics: str = ""
    audit: str = ""
    database: str = ""
    workflow: str = ""
    FIELDS = ['invoice_number', 'contract_reference', 'branch', 'amount_due', 'deposit_held', 'credit_note', 'balance_due', 'reference', 'status', 'analytics', 'audit', 'database', 'workflow']
    CONSTRAINTS = {'analytics': {'required': True}, 'audit': {'required': True}, 'database': {'required': True}, 'workflow': {'required': True}, 'amount_due': {'min': 0}, 'deposit_held': {'min': 0}, 'balance_due': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvoicingAndDeposits":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class MaintenanceScheduling:
    """Entity for capability maintenance_scheduling."""

    id: Optional[int] = None
    title: str = ""
    vehicle_reference: str = ""
    schedule_kind: str = 'date'
    due_date: str = '2026-09-03'
    due_mileage: int = 0
    workshop: str = ""
    downtime_days: int = 0
    estimated_cost: float = 0
    reference: str = ""
    status: str = 'open'

    FIELDS = ['title', 'vehicle_reference', 'schedule_kind', 'due_date', 'due_mileage', 'workshop', 'downtime_days', 'estimated_cost', 'reference', 'status']
    CONSTRAINTS = {'title': {'required': True}, 'schedule_kind': {'allowed_values': ['date', 'mileage']}, 'due_date': {'format': 'date'}, 'due_mileage': {'min': 0}, 'downtime_days': {'min': 0}, 'estimated_cost': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaintenanceScheduling":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class MultiBranchRollup:
    """Entity for capability multi_branch_rollup."""

    id: Optional[int] = None
    branch: str = ""
    period: str = ""
    fleet_utilisation: float = 0
    revenue: float = 0
    cost: float = 0
    profit: float = 0.0
    reference: str = ""
    status: str = 'open'

    analytics: str = ""
    dashboard: str = ""
    estate_registry: str = ""
    portfolio_rollup: str = ""
    FIELDS = ['branch', 'period', 'fleet_utilisation', 'revenue', 'cost', 'profit', 'reference', 'status', 'analytics', 'dashboard', 'estate_registry', 'portfolio_rollup']
    CONSTRAINTS = {'analytics': {'required': True}, 'dashboard': {'required': True}, 'estate_registry': {'required': True}, 'portfolio_rollup': {'required': True}, 'fleet_utilisation': {'min': 0, 'max': 100}, 'revenue': {'min': 0}, 'cost': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MultiBranchRollup":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class PricingAndRateCards:
    """Entity for capability pricing_and_rate_cards."""

    id: Optional[int] = None
    category: str = ""
    branch: str = ""
    season: str = ""
    duration_days: int = 1
    base_rate: float = 0
    mileage_charge: float = 0
    fuel_charge: float = 0
    late_return_charge: float = 0
    extras_charge: float = 0
    deposit_amount: float = 0
    override_reason: str = ""
    reference: str = ""
    status: str = 'open'

    analytics: str = ""
    audit: str = ""
    formula_executor: str = ""
    validation: str = ""
    FIELDS = ['category', 'branch', 'season', 'duration_days', 'base_rate', 'mileage_charge', 'fuel_charge', 'late_return_charge', 'extras_charge', 'deposit_amount', 'override_reason', 'reference', 'status', 'analytics', 'audit', 'formula_executor', 'validation']
    CONSTRAINTS = {'analytics': {'required': True}, 'audit': {'required': True}, 'formula_executor': {'required': True}, 'validation': {'required': True}, 'duration_days': {'min': 1}, 'base_rate': {'min': 0}, 'mileage_charge': {'min': 0}, 'fuel_charge': {'min': 0}, 'late_return_charge': {'min': 0}, 'extras_charge': {'min': 0}, 'deposit_amount': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PricingAndRateCards":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class RentalContractManagement:
    """Entity for capability rental_contract_management."""

    id: Optional[int] = None
    customer_name: str = ""
    vehicle_reference: str = ""
    branch: str = ""
    pickup_date: str = '2026-09-03'
    return_date: str = '2026-09-03'
    extension_days: int = 0
    daily_rate: float = 0
    deposit_amount: float = 0
    damage_notes: str = ""
    reference: str = ""
    status: str = 'open'

    FIELDS = ['customer_name', 'vehicle_reference', 'branch', 'pickup_date', 'return_date', 'extension_days', 'daily_rate', 'deposit_amount', 'damage_notes', 'reference', 'status']
    CONSTRAINTS = {'pickup_date': {'format': 'date'}, 'return_date': {'format': 'date'}, 'extension_days': {'min': 0}, 'daily_rate': {'min': 0}, 'deposit_amount': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RentalContractManagement":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ReportingAnalytics:
    """Entity for capability reporting_analytics."""

    id: Optional[int] = None
    metric: str = ""
    value: float = 0
    branch: str = ""
    period: str = ""
    query: str = ""
    reference: str = ""
    status: str = 'open'

    analytics: str = ""
    dashboard: str = ""
    memory: str = ""
    vector_search: str = ""
    FIELDS = ['metric', 'value', 'branch', 'period', 'query', 'reference', 'status', 'analytics', 'dashboard', 'memory', 'vector_search']
    CONSTRAINTS = {'analytics': {'required': True}, 'dashboard': {'required': True}, 'memory': {'required': True}, 'vector_search': {'required': True}, 'value': {'min': 0}, 'reference': {'required': True}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportingAnalytics":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {
    "audit_trail": AuditTrail,
    "fleet_registry": FleetRegistry,
    "invoicing_and_deposits": InvoicingAndDeposits,
    "maintenance_scheduling": MaintenanceScheduling,
    "multi_branch_rollup": MultiBranchRollup,
    "pricing_and_rate_cards": PricingAndRateCards,
    "rental_contract_management": RentalContractManagement,
    "reporting_analytics": ReportingAnalytics,
}
