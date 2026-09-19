"""Platform preconditions, run once at startup.
A block that mints its own id needs that id created BEFORE any
capability calls it. Generated from the factory's resource
obligations (R1c) rather than left to each handler to remember.

``resource_id(block_id)`` returns the id the ensure step received, or
None when the step has not run or did not succeed.

The id is scoped to the store root it was minted under. The block keeps its
registry under STORAGE_PATH, so an id cached while STORAGE_PATH pointed at
one directory is worthless once that variable moves: the block reads a
different (empty) registry and answers "Team access denied" while the
platform believes the precondition already holds. The suite isolates a
scratch STORAGE_PATH per phase, so that happens inside one process.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

_LOG = logging.getLogger(__name__)

#: block_id -> the id its ensure action returned.
RESOURCE_IDS: Dict[str, str] = {}
#: block_id -> why its ensure step did not produce an id.
RESOURCE_ERRORS: Dict[str, str] = {}
#: block_id -> the store root the cached id belongs to.
RESOURCE_SCOPES: Dict[str, str] = {}

PRECONDITIONS: Dict[str, Dict[str, Any]] = {'team': {'ensure': 'create_team', 'carry': 'team_id', 'input': {'user_id': 'system', 'name': 'Bakery Branch Operations Platform system', 'slug': 'bakery-branch-operations-platform-system'}, 'into': ['get_team_context', 'get_team', 'get_members', 'invite_member', 'set_role', 'check_permission', 'switch_team', 'delete_team']}}


def store_scope() -> str:
    """The store root the block registries live under, right now.

    Read per call, never cached: STORAGE_PATH legitimately changes between
    phases in one process (the suite points each phase at its own scratch
    directory) and the block resolves its own state file the same way.
    """
    raw = os.getenv("STORAGE_PATH") or "./data"
    try:
        return str(Path(raw).resolve())
    except OSError:  # unreadable/odd path: compare the literal value
        return str(raw)


def resource_id(block_id: str) -> Optional[str]:
    """The id ``ensure_all`` obtained for this block in THIS store root.

    ``None`` when the step has not run, did not succeed, or the cached id
    was minted against a different STORAGE_PATH -- the caller then runs
    ``ensure_all()`` again instead of handing a block an id its registry
    has never seen.
    """
    if RESOURCE_SCOPES.get(block_id) != store_scope():
        return None
    return RESOURCE_IDS.get(block_id)


def forget(block_id: str) -> None:
    """Drop a cached id and its error so the next ensure re-mints it."""
    RESOURCE_IDS.pop(block_id, None)
    RESOURCE_ERRORS.pop(block_id, None)
    RESOURCE_SCOPES.pop(block_id, None)


def ensure_all(force: bool = False) -> Dict[str, Any]:
    """Run every platform precondition. Idempotent; never raises."""
    from app.dispatch import execute

    scope = store_scope()
    for block_id, rule in PRECONDITIONS.items():
        if not force and RESOURCE_IDS.get(block_id) and (
            RESOURCE_SCOPES.get(block_id) == scope
        ):
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
            RESOURCE_SCOPES[block_id] = scope
            RESOURCE_ERRORS.pop(block_id, None)
        else:
            recovered = _recover(block_id, rule)
            if recovered:
                RESOURCE_IDS[block_id] = recovered
                RESOURCE_SCOPES[block_id] = scope
                RESOURCE_ERRORS.pop(block_id, None)
                _LOG.info("precondition %s already satisfied: %s", block_id, recovered)
                continue
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


#: block_id -> (list action, container key, id key, match key)
_RECOVERY = {
    "team": ("list_teams", "teams", "id", "slug"),
}


def _recover(block_id: str, rule: Dict[str, Any]) -> Optional[str]:
    """Look up the resource a refused ensure step says already exists."""
    spec = _RECOVERY.get(block_id)
    if not spec:
        return None
    action, container, id_key, match_key = spec
    wanted = str((rule.get("input") or {}).get(match_key) or "")
    from app.dispatch import execute

    try:
        answer = execute(block_id, {"user_id": "system"}, action=action)
    except Exception:  # noqa: BLE001 - recovery is best effort
        return None
    items = answer.get(container) if isinstance(answer, dict) else None
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and str(item.get(match_key) or "") == wanted:
            found = str(item.get(id_key) or "")
            return found or None
    return None
