"""Local block dispatch. No network, no store, no callback.

The old generated platforms answered a capability by POSTing to the operator's
block store. This imports the block that was vendored into this repository at
build time and calls it in-process, which is what makes the platform runnable
offline and independent of the factory's uptime.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict

_VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "blocks"
_CACHE: Dict[str, Any] = {}


class BlockNotVendored(RuntimeError):
    """Asked for a block this platform does not carry."""


def load_block(block_id: str):
    if block_id in _CACHE:
        return _CACHE[block_id]
    path = _VENDOR / block_id / "block.py"
    if not path.is_file():
        raise BlockNotVendored(
            f"{block_id} is not vendored in this platform (looked in {path})"
        )
    spec = importlib.util.spec_from_file_location(f"vendored_{block_id}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _CACHE[block_id] = module
    return module


BLOCK_CONTRACTS: Dict[str, Any] = {}


class DispatchContractError(ValueError):
    """Caller payload failed the harvested contract. Do not invent fields."""


#: Every envelope this dispatcher had to normalise, as
#: ``(block_id, lifted_keys)``. A silent normalisation is still a defect in
#: the generated handler; the WRITER contract probe reads this list so the
#: mismatch is NAMED rather than absorbed.
_LIFTED: list = []


def _required_fields(block_id: str) -> list:
    contract = BLOCK_CONTRACTS.get(block_id) or {}
    required = list(contract.get("input_required_fields") or [])
    for item in contract.get("declared_inputs") or []:
        name = item.get("name") if isinstance(item, dict) else None
        if name and item.get("required") and name not in required:
            required.append(name)
    return [field for field in required if field != "action"]


def _known_fields(block_id: str) -> set:
    """Closed field set from the harvested contract. Empty = no allow-list.

    Three sources, and the third is the one that was missing:

    * ``declared_inputs`` -- the block's CONFIG parameters, from block.json
      (backend, connection_string, theme, ...).
    * ``input_required_fields`` -- what the block refuses to run without.
    * ``input_keys_read_by_block`` -- the keys the block's own code actually
      reads off its payload at run time (table, values, where, file_path,
      user_id, ...). WORKAROUND, harvested from source; see
      CerebrumDev.ai#256 and Cerebrum-Blocks#90.

    Leaving the third one out is what made every generated platform inert.
    ``database`` declares only {input, backend, connection_string}, so a
    correct call -- ``{"table": "crew_logs", "values": {...}}`` -- had both
    keys counted as stray, folded into ``input`` by _adapt_input below, and
    handed to the block double-wrapped. ``_insert`` then read ``table=None``
    and ``values={}`` and emitted ``INSERT INTO None () VALUES ()``:

        database: Insert failed: near ")": syntax error

    One defect, four faces, measured on the booted zip of session
    sess_6400b6c: ``document_engine`` answered "No input files provided"
    holding a file_path, ``notification`` answered "block or tool name
    required for MCP channel" holding a block name, and ``team`` answered
    "Team access denied" holding a user_id. The platform built, shipped,
    booted and served all seventeen routes -- and could not persist a row.

    The fold itself stays: a key the block never reads is still a domain
    record and still belongs in ``input`` (the warehouse `audit` case the
    fold was written for). Only keys the block reads stay flat.
    """
    contract = BLOCK_CONTRACTS.get(block_id) or {}
    names: set = set()
    for item in contract.get("declared_inputs") or []:
        name = item.get("name") if isinstance(item, dict) else None
        if name and name != "action":
            names.add(name)
    for field in contract.get("input_required_fields") or []:
        if field != "action":
            names.add(field)
    for field in contract.get("input_keys_read_by_block") or []:
        if field and field != "action":
            names.add(str(field))
    return names


def _keys_read(block_id: str) -> set:
    """Only the keys the block's CODE reads off its payload at run time.

    Distinct from ``_known_fields``, which also carries block.json's declared
    CONFIG params. The distinction is what tells a declared ``input`` slot
    from one the block actually reads: measured on the vendored blocks,
    ``analytics``, ``database``, ``team`` and ``storage`` contain ZERO
    ``.get("input")`` -- they read their keys flat -- while ``workflow``
    reads one. Both facts are needed below.

    WORKAROUND: ``input_keys_read_by_block`` is regex-harvested from the
    vendored source because no manifest declares it yet. When block.json
    carries ``requires_inputs`` (Cerebrum-Blocks#90), that declaration
    replaces this read -- removal tracked in CerebrumDev.ai#256.
    """
    contract = BLOCK_CONTRACTS.get(block_id) or {}
    return {
        str(f) for f in (contract.get("input_keys_read_by_block") or []) if f
    }


def _envelope_mismatch(block_id: str, data: Dict[str, Any]) -> tuple:
    """Is the caller's record one level too deep for this block?

    Returns ``(buried, colliding)`` -- the keys the block reads that sit
    inside ``data["input"]`` instead of at the top level, and any of those
    that already exist at the top level with a different value.

    THE INCIDENT (residential-lettings, sess_6400b6c273414352, post-#254).
    ``unit_registry_and_vacancy_tracking`` called::

        execute("analytics", {"input": {"metric": "monthly_rent_gbp",
                                        "value": 1450.0, ...}},
                action="track_event")

    and got ``{'error': 'metric and value required'}``. Verified literally in
    the block source: ``AnalyticsBlock._track_event`` reads
    ``data.get("metric")`` and ``data.get("value")`` off the payload it is
    handed, and ``analytics``' block.json declares ``input`` only as a config
    slot -- the code never reads it. Both fields were present in the spec, so
    a plan-time audit that looks for NAMES passes; the block still saw
    neither. That is #254's class one level deeper, and the same file wrapped
    three different shapes with no rule.
    """
    reads = _keys_read(block_id)
    if not reads or "input" in reads:
        # The block genuinely reads an ``input`` key (``workflow`` does).
        # Its wrapper is the contract, not a mistake.
        return (), ()
    inner = data.get("input")
    if not isinstance(inner, dict):
        return (), ()
    buried = sorted(k for k in inner if k in reads and k != "action")
    colliding = sorted(
        k for k in buried if k in data and data[k] != inner[k]
    )
    return tuple(buried), tuple(colliding)


def _adapt_input(block_id: str, payload: Any, action: str | None) -> Dict[str, Any]:
    """Pass the caller payload through. Never invent Store fields (F18).

    A MISMATCHED ENVELOPE IS NEVER PASSED THROUGH SILENTLY. Either the
    record is normalised to the shape the block reads, or the call fails
    with the mismatch named -- it does not reach the block wearing a shape
    the block cannot read (owner's ruling R1d, 2026-09-01).
    """
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    known = _known_fields(block_id)

    buried, colliding = _envelope_mismatch(block_id, data)
    if colliding:
        # Two different values for the same field, one nested and one flat.
        # Normalising would have to choose, and choosing is inventing.
        verb = "appears" if len(colliding) == 1 else "appear"
        raise DispatchContractError(
            f"{block_id} envelope mismatch: {', '.join(colliding)} {verb} both "
            f"at the top level and inside 'input' with different values; "
            f"{block_id} reads them at the top level. Pass the record flat."
        )
    if buried:
        inner = dict(data.get("input") or {})
        for key in buried:
            data[key] = inner.pop(key)
        if inner:
            data["input"] = inner
        else:
            data.pop("input", None)
        _LIFTED.append((block_id, tuple(buried)))
    # Store blocks are action-dispatched: the domain record travels in the
    # block's declared ``input`` slot, with block params beside it. A handler
    # that passes the record flat gets every domain key refused as unknown --
    # measured on the warehouse `audit` capability, which declares
    # reference/status/quantity in its own model and had all three rejected.
    #
    # This is adaptation, not F18 fabrication. No value is invented and no
    # field is conjured to satisfy a validator: the caller's own record is
    # placed in the field the block declares for exactly it. If the caller
    # already supplied ``input``, nothing is moved.
    if known and "input" in known and "input" not in data:
        stray = {k: v for k, v in data.items() if k not in known}
        if stray:
            data = {k: v for k, v in data.items() if k in known}
            data["input"] = stray
    missing = [
        field for field in _required_fields(block_id)
        if field not in data or data[field] in (None, "")
    ]
    if missing:
        raise DispatchContractError(
            f"{block_id} missing required field(s): {', '.join(missing)}"
        )
    if known:
        unknown = sorted(str(key) for key in data if key not in known)
        if unknown:
            raise DispatchContractError(
                f"{block_id} unknown field(s): {', '.join(unknown)}"
            )
    return data


#: A block that answers with one of these has NOT succeeded. "partial" is the
#: word both the workflow and notification blocks use for "some of it failed"
#: -- workflow sets it on every step that raises, times out, names an unknown
#: block, or returns an error. Reading only "error" let a pipeline whose only
#: step failed come back as success.
_FAILED_STATUSES = {"error", "failed", "partial"}


def _failed_steps(result: Dict[str, Any]) -> list:
    """Sub-step failures the top-level status may not carry.

    Live, from the booted sess_6400b6c zip: punch_list_tracking returned
    ``ok: true`` wrapped around

        {"status": "partial", "results": [{"step_id": "step_0",
          "block": "database", "status": "failed",
          "error": "DatabaseBlock.__init__() missing 2 required positional
          arguments: 'hal_block' and 'config'"}]}

    The capability reported success. The row was never written.
    """
    steps = result.get("results")
    if not isinstance(steps, list):
        steps = result.get("steps")
    if not isinstance(steps, list):
        return []
    return [
        step for step in steps
        if isinstance(step, dict)
        and str(step.get("status") or "").lower() in {"error", "failed"}
    ]


def _error_envelope(block_id: str, action: str | None, error: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "block": block_id,
        "action": action,
        "error": error,
        "ok": False,
    }


def _force_utf8_stdio() -> None:
    """F13: a checkmark/emoji print must not become a charmap crash.

    Windows cp1252 consoles encode print() with the console codepage. A
    vendored block that prints one checkmark used to raise UnicodeEncodeError;
    execute() then swallowed that into a generic error envelope that looked
    like a domain refusal. Force UTF-8 on this process before the block runs.
    """
    import os
    import sys

    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, AttributeError):
            continue


_force_utf8_stdio()


def execute(
    block_id: str,
    payload: Dict[str, Any],
    action: str | None = None,
    params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Run a vendored block locally and return its result envelope.

    Real Store blocks are action-dispatched: the domain data travels as
    ``input`` and the operation name as ``action`` (each block declares a
    default in its block.json). A call with no action reaches blocks that
    answer "Unknown action" -- pass the one the capability needs.

    Missing required fields and unknown fields/params become an error
    envelope. A block refusal (status=error) is returned as-is — never
    rewritten to ok.
    """
    module = load_block(block_id)
    run = getattr(module, "run", None)
    if run is None:
        raise BlockNotVendored(f"{block_id} exposes no run() entry point")
    contract = BLOCK_CONTRACTS.get(block_id) or {}
    declared = set()
    for item in contract.get("declared_inputs") or []:
        name = item.get("name") if isinstance(item, dict) else None
        if name:
            declared.add(name)
    if (
        params
        and (contract.get("declared_inputs") or contract.get("input_required_fields"))
    ):
        extra = sorted(
            str(key) for key in params if key not in declared and key != "action"
        )
        if extra:
            return _error_envelope(
                block_id, action, f"unknown param(s): {', '.join(extra)}"
            )
    kwargs = dict(params or {})
    if action is not None:
        kwargs["action"] = action
    try:
        adapted = _adapt_input(block_id, payload, action)
    except DispatchContractError as exc:
        return _error_envelope(block_id, action, str(exc))
    # A block-level failure comes back as data, not as an exception. The
    # Store's shim raises RuntimeError on an error envelope, which destroys
    # the diagnosis: a handler (and a failing test) sees "Input validation
    # failed" with no block name and no field list. Structural failures --
    # a block that is not vendored -- still raise above.
    _force_utf8_stdio()
    try:
        result = run(input=adapted, **kwargs)
    except BlockNotVendored:
        raise
    except UnicodeEncodeError as exc:
        return _error_envelope(
            block_id,
            action,
            f"UnicodeEncodeError on block stdout (encoding, not domain): {exc}",
        )
    except Exception as exc:
        return _error_envelope(
            block_id, action, f"{type(exc).__name__}: {exc}"
        )
    if isinstance(result, dict):
        status = str(result.get("status") or "").lower()
        failed = _failed_steps(result)
        if status in _FAILED_STATUSES or result.get("ok") is False or failed:
            refused = dict(result)
            refused["status"] = status if status in _FAILED_STATUSES else "error"
            refused.setdefault("block", block_id)
            refused["ok"] = False
            if failed and not refused.get("error"):
                refused["error"] = "; ".join(
                    "%s (%s): %s" % (
                        step.get("step_id") or "step",
                        step.get("block") or "?",
                        str(step.get("error") or step.get("status"))[:160],
                    )
                    for step in failed
                )
            return refused
    return result
