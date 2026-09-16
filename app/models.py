"""Domain models for this platform.

Plain dataclasses on purpose: the delivered platform must run with no
ORM, no service, and no network. Persistence is in app/store.py.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RecordCheckIn:
    """Entity for capability record_check_in."""

    id: Optional[int] = None
    reference: str = ""
    guest_name: str = ""
    room_number: str = ""
    checked_in_at: str = ""
    guests_count: int = 0
    status: str = ""
    notes: str = ""

    FIELDS = ['reference', 'guest_name', 'room_number', 'checked_in_at', 'guests_count', 'status', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': True}, 'checked_in_at': {'format': 'datetime', 'required': False}, 'guests_count': {'max': 20, 'min': 1, 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'notes': {'required': False}}
    ENTITY = 'record_check_in'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordCheckIn":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class ListTodaysCheckIns:
    """Entity for capability list_todays_check_ins."""

    id: Optional[int] = None
    reference: str = ""
    check_in_date: str = ""
    room_number: str = ""
    guest_name: str = ""
    check_in_count: int = 0
    status: str = ""
    notes: str = ""

    FIELDS = ['reference', 'check_in_date', 'room_number', 'guest_name', 'check_in_count', 'status', 'notes']
    CONSTRAINTS = {'reference': {'required': True}, 'check_in_date': {'required': True}, 'room_number': {'required': True}, 'guest_name': {'required': True}, 'check_in_count': {'max': 500, 'min': 0, 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}, 'notes': {'required': False}}
    ENTITY = 'list_todays_check_ins'
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ListTodaysCheckIns":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


MODELS = {'record_check_in': RecordCheckIn, 'list_todays_check_ins': ListTodaysCheckIns}
