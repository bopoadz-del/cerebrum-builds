"""Capability contracts: the schema the routes enforce."""

from __future__ import annotations

from app.cerebrum_product_kernel.contract.registry import (
    CAPABILITIES,
    contract_for,
    entity_for,
)
from app.cerebrum_product_kernel.contract.runtime import execute_action
from app.cerebrum_product_kernel.contract.schema_validation import validate_record

__all__ = (
    "CAPABILITIES",
    "contract_for",
    "entity_for",
    "execute_action",
    "validate_record",
)
