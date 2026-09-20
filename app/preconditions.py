"""Platform preconditions, run once at startup.
A block that mints its own id needs that id created BEFORE any
capability calls it. Generated from the factory's resource
obligations (R1c) rather than left to each handler to remember.

``resource_id(block_id)`` returns the id the ensure step received, or
None when the step has not run or did not succeed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

_LOG = logging.getLogger(__name__)

#: block_id -> the id its ensure action returned.
RESOURCE_IDS: Dict[str, str] = {}
#: block_id -> why its ensure step did not produce an id.
RESOURCE_ERRORS: Dict[str, str] = {}

#: block_id -> the one id it mints and every capability then carries.
#:
#: R1c: a block that mints its own id needs that id created BEFORE any
#: capability calls it. ``team`` refuses a second ``create_team`` for the same
#: slug ("Team slug already exists"), so the platform creates its team once at
#: boot and every later call carries the returned ``team_id`` instead of
#: asking for another team.
PRECONDITIONS: Dict[str, Dict[str, Any]] = {
    "team": {
        "ensure": "create_team",
        "input": {
            "name": "construction platform team",
            "slug": "construction-platform-team",
            "user_id": "system",
        },
        "carry": "team_id",
    },
}


def resource_id(block_id: str) -> Optional[str]:
    """The id ``ensure_all`` obtained for this block, if any."""
    return RESOURCE_IDS.get(block_id)


def ensure_all() -> Dict[str, Any]:
    """Run every platform precondition. Idempotent; never raises."""
    from app.dispatch import execute

    for block_id, rule in PRECONDITIONS.items():
        if RESOURCE_IDS.get(block_id):
            continue
        try:
            result = execute(
                block_id, dict(rule["input"]), action=rule["ensure"]
            )
        except Exception as exc:  # noqa: BLE001 - boot must not die
            RESOURCE_ERRORS[block_id] = "%s: %s" % (
                type(exc).__name__, exc,
            )
            _LOG.warning(
                "precondition %s %s raised: %s",
                block_id, rule["ensure"], exc,
            )
            continue
        got = None
        if isinstance(result, dict):
            got = result.get(rule["carry"])
            if got is None and isinstance(result.get("result"), dict):
                got = result["result"].get(rule["carry"])
        if got:
            RESOURCE_IDS[block_id] = str(got)
            RESOURCE_ERRORS.pop(block_id, None)
        else:
            RESOURCE_ERRORS[block_id] = str(
                (result or {}).get("error") if isinstance(result, dict)
                else result
            )[:200]
            _LOG.warning(
                "precondition %s %s returned no %s: %s",
                block_id, rule["ensure"], rule["carry"],
                RESOURCE_ERRORS[block_id],
            )
    return {"ids": dict(RESOURCE_IDS), "errors": dict(RESOURCE_ERRORS)}
