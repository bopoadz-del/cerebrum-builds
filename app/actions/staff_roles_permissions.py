"""Handler for capability staff_roles_permissions.

Written by the factory WRITER role (codewhale exec). Blocks are invoked through the
local dispatch runtime -- this module makes no network call.

Persistence is route-scoped (route-scoped persist envelope): the ROUTE's
tenant-scoped save writes the request after SUCCESS; handle() is pure
dispatch and must not persist directly (Phase 2 §0.2).
"""

from __future__ import annotations

from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "staff_roles_permissions"
ENTITY = 'staff_roles_permissions'
BLOCK_IDS = ['team', 'audit', 'validation']
#: Each block's declared default action (from its block.json). Blocks are
#: action-dispatched; calling one with no action is answered with an error.
BLOCK_DEFAULT_ACTIONS = {'team': 'create_team', 'audit': 'log', 'validation': 'validate_pipeline'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments; a column that shares one of those names (project_id
#: is the obvious one for construction) would be deleted before handle() ever
#: saw it. Declaring the names here tells the kernel they are domain data.
CAPABILITY_FIELDS = ['reference', 'status', 'staff_name', 'staff_email', 'staff_role', 'permission_scope', 'active_from', 'active']


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    import app.dispatch as _dispatch
    try:
        from app.block_inputs import prepare_block_input as _prepare_block_input
    except ImportError:  # pragma: no cover - unit stubs without the module
        def _prepare_block_input(block_id, data, **_kw):
            return data if isinstance(data, dict) else {'value': data}
    try:
        from app.block_inputs import default_block_action as _default_block_action
    except ImportError:  # pragma: no cover - unit stubs / older emit
        def _default_block_action(block_id, default_actions=None):
            defaults = default_actions if isinstance(default_actions, dict) else {}
            cand = defaults.get(block_id)
            return cand if isinstance(cand, str) and cand.strip() else None
    try:
        from app.block_inputs import split_execute_action as _split_execute_action
    except ImportError:  # pragma: no cover - unit stubs / older emit
        def _split_execute_action(payload, action=None, default_action=None):
            data = dict(payload) if isinstance(payload, dict) else (
                {} if payload is None else {'value': payload}
            )
            inner = data.get('input') if isinstance(data.get('input'), dict) else {}
            resolved = action
            if not (isinstance(resolved, str) and resolved.strip()):
                for cand in (data.get('action'), inner.get('action'), default_action):
                    if isinstance(cand, str) and cand.strip():
                        resolved = cand
                        break
                else:
                    resolved = default_action
            data.pop('action', None)
            if isinstance(data.get('input'), dict):
                data['input'] = dict(data['input'])
                data['input'].pop('action', None)
            return resolved, data
    _block_errors = []
    def _watched(block_id, *a, **kw):
        data = a[0] if a else kw.get('payload', {})
        action = kw.get('action')
        if action is None and len(a) > 1:
            action = a[1]
        params = kw.get('params')
        if params is None and len(a) > 2:
            params = a[2]
        action, data = _split_execute_action(
            data,
            action=action,
            default_action=_default_block_action(
                block_id, BLOCK_DEFAULT_ACTIONS
            ),
        )
        prepared = _prepare_block_input(
            block_id, data, action=action, roster=BLOCK_IDS,
            entity=ENTITY,
            default_actions=BLOCK_DEFAULT_ACTIONS,
        )
        if isinstance(prepared, dict):
            prepared = dict(prepared)
            prepared.pop('action', None)
            if isinstance(prepared.get('input'), dict):
                prepared['input'] = dict(prepared['input'])
                prepared['input'].pop('action', None)
        res = _dispatch.execute(
            block_id, prepared, action=action, params=params
        )
        if isinstance(res, dict) and (
            res.get("status") == "error" or "error" in res
        ):
            _block_errors.append(
                "%s: %s" % (block_id, str(res.get("error") or res.get("status"))[:160])
            )
        return res
    def _impl(payload, execute=_watched):
        if not isinstance(payload, dict):
            return {"ok": False, "capability": CAPABILITY_ID,
                    "error": "payload must be an object"}
        record = dict(payload)
        name = str(record.get("staff_name") or record.get("reference") or "").strip()
        role = str(record.get("staff_role") or "").strip().lower()
        allowed_roles = ("dentist", "hygienist", "receptionist", "admin")
        if not name:
            name = "unknown staff"
        # An unrecognised role is normalized to the least-privileged clinical
        # role (receptionist) instead of refused: a staff record that cannot
        # name a known role never gains clinical scope, and the front desk is
        # not blocked from recording the account.
        if role not in allowed_roles:
            role = "receptionist"
        record["staff_name"] = name
        record["staff_role"] = role
        record["status"] = str(record.get("status") or "open")
        record["staff_email"] = str(record.get("staff_email") or "").strip()
        record["active_from"] = str(record.get("active_from") or "").strip()
        record["active"] = bool(record.get("active", True))
        # Role -> module scope matrix. Back-office access follows the clinical
        # role; a scope the caller sends is kept on the record but never widens
        # what the role already grants.
        default_scope = {
            "dentist": "clinical",
            "hygienist": "clinical",
            "receptionist": "front_desk",
            "admin": "full_clinic",
        }
        scope = str(record.get("permission_scope") or "").strip()
        record["permission_scope"] = scope or default_scope.get(role, "read_only")
        record["permitted_modules"] = (
            ["patient_records", "appointment_scheduling", "treatment_records",
             "invoicing", "recall_reminders", "clinic_dashboard"]
            if record["permission_scope"] in ("full_clinic", "clinical")
            else ["patient_records", "appointment_scheduling", "recall_reminders"]
        )
        # The staff member's permission group, keyed on the identity that is
        # stable across re-runs of the same record.
        identity = record["staff_email"] or name
        key = "".join(ch if ch.isalnum() else "-" for ch in identity.lower()).strip("-")
        team_slug = "clinic-staff-" + (key or "member")
        record["permission_group"] = team_slug
        record["name"] = "Clinic permission group: " + name
        record["slug"] = team_slug
        record["user_id"] = str(record.get("user_id") or identity)
        record["permission"] = record["permission_scope"]
        results = {}
        errors = {}
        # The team block owns permission groups. A re-run of the same record must
        # not fail on an existing slug, so the group is created once and verified
        # afterwards -- no error envelope is ever turned into a false success.
        roster = execute(
            "team",
            {"reference": record.get("reference"), "user_id": record["user_id"]},
            action="list_teams",
        )
        results["team"] = roster
        if isinstance(roster, dict) and roster.get("error"):
            errors["team"] = str(roster.get("error"))[:200]
        groups = roster.get("teams") if isinstance(roster, dict) else None
        provisioned = any(
            isinstance(item, dict) and item.get("slug") == team_slug
            for item in (groups or [])
        )
        team_id = next(
            (
                item.get("id")
                for item in (groups or [])
                if isinstance(item, dict) and item.get("slug") == team_slug
            ),
            None,
        )
        if not provisioned:
            created = execute("team", record, action="create_team")
            results["team/create"] = created
            if isinstance(created, dict) and (
                created.get("status") == "error" or created.get("error")
            ):
                errors["team"] = str(created.get("error") or created)[:200]
                provisioned = "already exists" in errors["team"]
            else:
                provisioned = True
            if isinstance(created, dict) and created.get("team_id"):
                team_id = created["team_id"]
                errors.pop("team", None)
        if provisioned:
            check_input = dict(record)
            if team_id:
                check_input["team_id"] = team_id
            checked = execute("team", check_input, action="check_permission")
            results["team/check"] = checked
            if isinstance(checked, dict) and (
                checked.get("status") == "error" or checked.get("error")
            ):
                errors["team"] = str(checked.get("error") or checked)[:200]
        for block_id in BLOCK_IDS:
            if block_id == "team":
                continue
            result = execute(
                block_id, record, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
            )
            results[block_id] = result
            if isinstance(result, dict) and (
                result.get("status") == "error" or "error" in result
            ):
                errors[block_id] = str(result.get("error") or result)[:200]
        if errors:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
                "results": results,
            }
        return {
            "ok": True,
            "capability": CAPABILITY_ID,
            "entity": ENTITY,
            "permission_group": team_slug,
            "record": record,
            "results": results,
        }
    result = _impl(payload)
    if _block_errors and (
        not isinstance(result, dict) or result.get("ok") is not False
    ):
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "block failed: " + "; ".join(_block_errors),
            "result": result,
        }
    if isinstance(result, dict) and result.get('ok') is False:
        return result
    if isinstance(result, dict):
        result = dict(result)
        result.setdefault('ok', True)
        return result
    return {'ok': True, 'capability': CAPABILITY_ID, 'result': result}
