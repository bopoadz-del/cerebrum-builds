"""Platform preconditions, run once at startup.
A block that mints its own id needs that id created BEFORE any
capability calls it. Generated from the factory's resource
obligations (R1c) rather than left to each handler to remember.

``resource_id(block_id)`` returns the id the ensure step received, or
None when the step has not run or did not succeed.

Two invariants this module owns, both learned from a live red product gate:

* the cache is scoped to the persistence root. A minted id names state that
  lives under ``STORAGE_PATH``, so re-pointing that path invalidates it;
  ``_bind_storage_root`` forgets ids from another root and the id is
  re-ensured there instead of being handed out stale.
* the ensure step is idempotent. ``create_team`` refuses a slug that already
  exists, so ``_recover`` asks the block for the id it already minted before
  anything is created. Without it, re-ensuring a root that already holds the
  platform team errors and every capability bound to the block is handed no
  id -- the same refusal this module exists to prevent, one layer down.
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
#: The persistence root the cached ids were minted under.
RESOURCE_ROOT: Dict[str, str] = {"storage": ""}

PRECONDITIONS: Dict[str, Dict[str, Any]] = {'team': {'ensure': 'create_team', 'carry': 'team_id', 'recover': {'action': 'list_teams', 'key': 'teams', 'match': 'slug', 'id': 'id'}, 'input': {'user_id': 'system', 'name': 'Facility Management Platform for Schools system', 'slug': 'facility-management-platform-for-schools-system'}, 'into': ['get_team_context', 'get_team', 'get_members', 'invite_member', 'set_role', 'check_permission', 'switch_team', 'delete_team']}}


def storage_root() -> str:
    """The persistence root the vendored blocks write their state under."""
    raw = os.environ.get("STORAGE_PATH") or "."
    try:
        return str(Path(raw).resolve())
    except OSError:  # pragma: no cover - unresolvable path
        return str(raw)


def _bind_storage_root() -> None:
    """Forget ids minted under a different persistence root.

    A minted id is stored in block state under ``STORAGE_PATH`` (the team
    block keeps its teams and memberships in ``<root>/team/state.json``).
    The id itself was cached in this module's memory, which outlives a
    re-pointed ``STORAGE_PATH`` -- measured live in this build: the pilot
    suite re-points STORAGE_PATH mid-session, the cached id survived, and
    the team block answered "Team access denied" for a team that existed
    only under the previous root, so auto_assignment, workforce_management
    and role_based_access all refused a payload built from their own
    schema. Re-ensuring per root is the fix; the id is only valid inside
    the root that holds the state it names.
    """
    root = storage_root()
    if RESOURCE_ROOT.get("storage") == root:
        return
    RESOURCE_ROOT["storage"] = root
    RESOURCE_IDS.clear()
    RESOURCE_ERRORS.clear()


def owner_user_id(block_id: str) -> Optional[str]:
    """The user the precondition's ensure step belonged to, if declared."""
    rule = PRECONDITIONS.get(str(block_id or "")) or {}
    user = (rule.get("input") or {}).get("user_id")
    return str(user) if user else None


def resource_id(block_id: str) -> Optional[str]:
    """The id ``ensure_all`` obtained for this block, in this store root."""
    _bind_storage_root()
    return RESOURCE_IDS.get(block_id)


def _result_body(result: Any) -> Dict[str, Any]:
    body = result if isinstance(result, dict) else {}
    inner = body.get("result")
    if isinstance(inner, dict):
        return inner
    return body


def _recover(block_id: str, rule: Dict[str, Any]) -> Optional[str]:
    """Adopt a resource an earlier ensure step already minted.

    The ensure step is not idempotent by itself: ``create_team`` refuses a
    slug that already exists. So after a cache reset for a root that already
    holds the platform team, re-running ``ensure`` would error and every
    capability bound to the block would be handed no id at all -- the same
    "Team access denied" this module exists to prevent, one layer down.
    The block is asked what it already holds before anything is created.
    """
    from app.dispatch import execute

    recover = rule.get("recover") or {}
    action = recover.get("action")
    if not action:
        return None
    try:
        result = execute(block_id, dict(rule.get("input") or {}), action=action)
    except Exception as exc:  # noqa: BLE001 - recovery is best-effort, named
        _LOG.debug("precondition %s recover %s raised: %s", block_id, action, exc)
        return None
    items = _result_body(result).get(recover.get("key") or "items") or []
    if not isinstance(items, list):
        return None
    want = (rule.get("input") or {}).get(recover.get("match") or "slug")
    for item in items:
        if not isinstance(item, dict):
            continue
        if want is not None and item.get(recover.get("match") or "slug") != want:
            continue
        adopted = item.get(recover.get("id") or "id")
        if adopted:
            return str(adopted)
    return None


def ensure_all() -> Dict[str, Any]:
    """Run every platform precondition. Idempotent; never raises."""
    from app.dispatch import execute

    _bind_storage_root()
    for block_id, rule in PRECONDITIONS.items():
        if RESOURCE_IDS.get(block_id):
            continue
        adopted = _recover(block_id, rule)
        if adopted:
            RESOURCE_IDS[block_id] = adopted
            RESOURCE_ERRORS.pop(block_id, None)
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
