"""Team Block — crew roster create/list. Offline only."""

from __future__ import annotations

from typing import Any, Dict, List

from vendor.cerebrum.core.universal_base import UniversalBlock


class TeamBlock(UniversalBlock):
    name = "team"
    version = "1.0.0"
    description = "Create and list operational teams"
    layer = 3
    tags = ["team", "roster", "ops"]
    requires = []
    default_config = {}
    ui_schema = {
        "input": {"type": "json", "placeholder": '{"name": "crew"}', "multiline": True},
        "output": {"type": "json", "fields": [{"name": "team_id", "type": "text"}]},
        "params": [
            {
                "name": "action",
                "type": "select",
                "options": ["create_team", "add_member", "list_members", "status"],
                "default": "create_team",
            }
        ],
    }

    def __init__(self, hal_block=None, config: Dict = None):
        super().__init__(hal_block, config)
        self._teams: Dict[str, Dict[str, Any]] = {}

    async def process(self, input_data: Any, params: Dict = None) -> Dict:
        params = params or {}
        data = input_data if isinstance(input_data, dict) else {"name": str(input_data)}
        action = params.get("action") or "create_team"
        if action == "create_team":
            return self._create(data)
        if action == "add_member":
            return self._add_member(data)
        if action == "list_members":
            return self._list(data)
        if action == "status":
            return {"teams": len(self._teams), "status": "ok"}
        return {"error": f"Unknown action: {action}"}

    def _create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        seed = data.get("result") if isinstance(data.get("result"), dict) else {}
        name = str(data.get("name") or seed.get("reference") or data.get("reference") or "crew")
        members: List[Any] = list(data.get("members") or seed.get("members") or [])
        team_id = str(data.get("team_id") or f"team-{name}")
        self._teams[team_id] = {"team_id": team_id, "name": name, "members": members}
        return {"created": True, "team_id": team_id, "name": name, "member_count": len(members)}

    def _add_member(self, data: Dict[str, Any]) -> Dict[str, Any]:
        team_id = str(data.get("team_id") or next(iter(self._teams), "team-crew"))
        team = self._teams.setdefault(team_id, {"team_id": team_id, "name": team_id, "members": []})
        member = data.get("member") or data.get("name") or "operator"
        team["members"].append(member)
        return {"added": True, "team_id": team_id, "member": member}

    def _list(self, data: Dict[str, Any]) -> Dict[str, Any]:
        team_id = str(data.get("team_id") or next(iter(self._teams), "team-crew"))
        team = self._teams.get(team_id, {"team_id": team_id, "members": []})
        return {"team_id": team_id, "members": team.get("members", [])}
