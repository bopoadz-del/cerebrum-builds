"""Schema validation shared by the kernel, the routes and the pilot suite."""

from __future__ import annotations

from typing import Any, Dict

from app.auth import validate_payload
from app.cerebrum_product_kernel.contract.registry import contract_for


def validate_record(capability_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate against the capability's declared FIELDS + CONSTRAINTS.

    Raises ``fastapi.HTTPException`` 422 with a named reason, exactly as the
    route does — there is one contract, not a route contract and a kernel one.
    """
    if contract_for(capability_id) is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="unknown_capability")
    return validate_payload(capability_id, payload)
