"""One fail-closed block call for every capability handler.

Written by the factory WRITER role (codewhale exec)

Product contract, in one place so no handler can drift from it:

* the block's input is built by ``app.block_inputs.prepare_block_input`` --
  the caller is never asked for a block-contract key (channel, steps, table,
  file path, topic);
* ``action`` travels as the ``action=`` keyword, never inside the domain
  payload (the one documented exception is a block whose own ``input_schema``
  declares ``action`` as a field -- ``hospitality_connectors`` -- and that is
  passed in ``payload_extra`` on purpose, named in the handler);
* EVERY block call is watched. A block that answers an error, and a handler
  that keeps going, is the LotDesk defect: the route would report success and
  persist a record whose work never happened. The runner returns the list of
  block failures and the caller refuses.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

import app.dispatch as dispatch

from app.block_inputs import prepare_block_input

PRODUCT_NAME = "Hotel Operations"


def block_runner(
    *,
    entity: str,
    roster: Sequence[str],
    default_actions: Dict[str, str],
) -> "BlockRunner":
    return BlockRunner(entity=entity, roster=roster, default_actions=default_actions)


_FAILED = {"error", "failed", "partial", "refused"}


class BlockRunner:
    """Call vendored blocks and remember every refusal they answer with."""

    def __init__(self, *, entity: str, roster: Sequence[str], default_actions: Dict[str, str]) -> None:
        self.entity = entity
        self.roster = list(roster)
        self.default_actions = dict(default_actions or {})
        self.errors: List[str] = []
        self.calls: List[Dict[str, Any]] = []

    # -- calling -----------------------------------------------------------
    def action_for(self, block_id: str) -> Optional[str]:
        value = self.default_actions.get(block_id)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def __call__(
        self,
        block_id: str,
        payload: Any,
        *,
        action: Optional[str] = None,
        payload_extra: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        resolved = action or self.action_for(block_id)
        data = dict(payload) if isinstance(payload, dict) else {"value": payload}
        prepared = prepare_block_input(
            block_id,
            data,
            action=resolved,
            roster=self.roster,
            product_name=PRODUCT_NAME,
            entity=self.entity,
            default_actions=self.default_actions,
        )
        if not isinstance(prepared, dict):
            prepared = {"value": prepared}
        prepared = dict(prepared)
        prepared.pop("action", None)
        if isinstance(prepared.get("input"), dict):
            prepared["input"] = dict(prepared["input"])
            prepared["input"].pop("action", None)
        if payload_extra:
            # A block whose own input_schema declares a field the dispatch
            # contract does not carry (hospitality_connectors reads its
            # operation out of its payload) gets it here, and only here.
            prepared.update(payload_extra)
        try:
            result = dispatch.execute(block_id, prepared, action=resolved, params=params)
        except Exception as exc:  # a block that cannot even load is a refusal
            message = f"{block_id}: {type(exc).__name__}: {exc}"
            self.errors.append(message)
            self.calls.append({"block": block_id, "action": resolved, "ok": False, "error": str(exc)})
            return {"status": "error", "block": block_id, "error": str(exc), "ok": False}
        ok = True
        error_text = ""
        if isinstance(result, dict):
            status = str(result.get("status") or "").lower()
            if status in _FAILED or result.get("ok") is False or result.get("error"):
                ok = False
                error_text = str(result.get("error") or status or "refused")[:200]
        if not ok:
            self.errors.append(f"{block_id}: {error_text}")
        self.calls.append(
            {"block": block_id, "action": resolved, "ok": ok, "error": error_text}
        )
        return result if isinstance(result, dict) else {"value": result}

    # -- reporting ---------------------------------------------------------
    def refusal(self) -> Optional[Dict[str, Any]]:
        """The handler's refusal envelope, or None when every block held."""
        if not self.errors:
            return None
        return {
            "ok": False,
            "error": "block failed: " + "; ".join(self.errors)[:800],
            "blocks": list(self.calls),
        }

    def report(self) -> List[Dict[str, Any]]:
        return list(self.calls)
