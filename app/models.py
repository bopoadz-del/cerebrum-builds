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
    reference: str = ""
    actor: str = ""
    change_type: str = 'create'
    subject_capability: str = ""
    changed_at: str = '2026-09-03T10:00:00'
    status: str = 'open'

    FIELDS = ['reference', 'actor', 'change_type', 'subject_capability', 'changed_at', 'status']
    ENTITY = 'audit_trail'
    CONSTRAINTS = {'reference': {'required': True}, 'actor': {'required': True}, 'change_type': {'allowed_values': ['create', 'update', 'delete'], 'required': False}, 'subject_capability': {'required': False}, 'changed_at': {'format': 'datetime', 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
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
class CheckinNotifications:
    """Entity for capability checkin_notifications."""

    id: Optional[int] = None
    reference: str = ""
    guest_name: str = ""
    room_number: str = ""
    channel: str = 'mcp'
    recipient: str = ""
    status: str = 'open'

    FIELDS = ['reference', 'guest_name', 'room_number', 'channel', 'recipient', 'status']
    ENTITY = 'checkin_notifications'
    CONSTRAINTS = {'reference': {'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': True}, 'channel': {'allowed_values': ['mcp', 'email'], 'required': False}, 'recipient': {'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckinNotifications":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class DailyCheckinSummary:
    """Entity for capability daily_checkin_summary."""

    id: Optional[int] = None
    reference: str = ""
    summary_date: str = '2026-09-03'
    arrivals_count: int = 0
    occupancy_percent: float = 0
    no_show_count: int = 0
    status: str = 'open'

    FIELDS = ['reference', 'summary_date', 'arrivals_count', 'occupancy_percent', 'no_show_count', 'status']
    ENTITY = 'daily_checkin_summary'
    CONSTRAINTS = {'reference': {'required': True}, 'summary_date': {'format': 'date', 'required': True}, 'arrivals_count': {'min': 0, 'max': 500, 'required': False}, 'occupancy_percent': {'min': 0, 'max': 100, 'required': False}, 'no_show_count': {'min': 0, 'max': 100, 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DailyCheckinSummary":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class GuestNotesAndPreferences:
    """Entity for capability guest_notes_and_preferences."""

    id: Optional[int] = None
    reference: str = ""
    guest_name: str = ""
    room_number: str = ""
    preference: str = ""
    note: str = ""
    status: str = 'open'

    FIELDS = ['reference', 'guest_name', 'room_number', 'preference', 'note', 'status']
    ENTITY = 'guest_notes_and_preferences'
    CONSTRAINTS = {'reference': {'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': False}, 'preference': {'required': False}, 'note': {'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuestNotesAndPreferences":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class RecordCheckin:
    """Entity for capability record_checkin."""

    id: Optional[int] = None
    reference: str = ""
    guest_name: str = ""
    room_number: str = ""
    nights: int = 1
    arrival_time: str = '10:00:00'
    notes: str = ""
    status: str = 'open'

    FIELDS = ['reference', 'guest_name', 'room_number', 'nights', 'arrival_time', 'notes', 'status']
    ENTITY = 'record_checkin'
    CONSTRAINTS = {'reference': {'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': True}, 'nights': {'min': 1, 'max': 30, 'required': True}, 'arrival_time': {'format': 'time', 'required': True}, 'notes': {'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordCheckin":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class RoomAvailabilityCheck:
    """Entity for capability room_availability_check."""

    id: Optional[int] = None
    reference: str = ""
    room_number: str = ""
    check_in_date: str = '2026-09-03'
    check_out_date: str = '2026-09-03'
    is_available: bool = False
    status: str = 'open'

    FIELDS = ['reference', 'room_number', 'check_in_date', 'check_out_date', 'is_available', 'status']
    ENTITY = 'room_availability_check'
    CONSTRAINTS = {'reference': {'required': True}, 'room_number': {'required': True}, 'check_in_date': {'format': 'date', 'required': True}, 'check_out_date': {'format': 'date', 'required': True}, 'is_available': {'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoomAvailabilityCheck":
        known = {}
        for k, v in (data or {}).items():
            if k == "id":
                continue
            attr = cls._FIELD_PY.get(k, k)
            if k in cls.FIELDS or attr in cls._FIELD_JSON:
                known[attr] = v
        return cls(id=(data or {}).get("id"), **known)


@dataclass
class TodaysArrivalsBoard:
    """Entity for capability todays_arrivals_board."""

    id: Optional[int] = None
    reference: str = ""
    arrival_date: str = '2026-09-03'
    guest_name: str = ""
    room_number: str = ""
    arrived: bool = False
    arrivals_count: int = 0
    status: str = 'open'

    FIELDS = ['reference', 'arrival_date', 'guest_name', 'room_number', 'arrived', 'arrivals_count', 'status']
    ENTITY = 'todays_arrivals_board'
    CONSTRAINTS = {'reference': {'required': True}, 'arrival_date': {'format': 'date', 'required': True}, 'guest_name': {'required': True}, 'room_number': {'required': True}, 'arrived': {'required': False}, 'arrivals_count': {'min': 0, 'max': 200, 'required': False}, 'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True}}
    _FIELD_PY = {}
    _FIELD_JSON = {}

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {self._FIELD_JSON.get(k, k): v for k, v in raw.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TodaysArrivalsBoard":
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
    "checkin_notifications": CheckinNotifications,
    "daily_checkin_summary": DailyCheckinSummary,
    "guest_notes_and_preferences": GuestNotesAndPreferences,
    "record_checkin": RecordCheckin,
    "room_availability_check": RoomAvailabilityCheck,
    "todays_arrivals_board": TodaysArrivalsBoard,
}
