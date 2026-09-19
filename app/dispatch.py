"""Local block dispatch for the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

Every block this platform binds was vendored into ``vendor/blocks/<id>/`` at
build time and is pinned by ``blocks.lock.json``. Handlers call
``execute(block_id, payload, action=...)``; nothing here reaches the network,
the Factory, or a block store. Real Store blocks are action-dispatched, so the
operation travels as the ``action=`` keyword and never inside the payload dict.

Envelope rules
--------------
* a block answer with ``status`` in ``error|failed|partial``, ``ok: false``, or
  a failed workflow step is returned as an error envelope (never rewritten to
  success);
* a block that raises is returned as ``status=error`` with the block named --
  a handler and a failing test can then see which block refused, instead of a
  bare stack trace;
* a vendored module that cannot be imported (a build-time vendoring defect, not
  a domain refusal) falls back to the factory-mirror shim in
  ``app/offline_blocks.py`` and the answer says so (``vendored: false``). No
  shim is ever used to fake a successful Store call.

Scope
-----
READS  ``vendor/blocks/**`` (import only), ``STORAGE_PATH`` via the shims.
WRITES nothing.
NEVER  network, HTTP store callbacks, ``vendor/**`` writes.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "blocks"
_CACHE: Dict[str, Any] = {}
_LOAD_FAILURES: Dict[str, str] = {}
_RESOLVE_FAILURES: Dict[str, str] = {}

_FAILED_STATUSES = {"error", "failed", "partial"}


class BlockNotVendored(RuntimeError):
    """Asked for a block this platform does not carry."""


def load_block(block_id: str):
    """Import ``vendor/blocks/<id>/block.py`` and return the module."""
    if block_id in _CACHE:
        return _CACHE[block_id]
    path = _VENDOR / block_id / "block.py"
    if not path.is_file():
        raise BlockNotVendored(
            f"{block_id} is not vendored in this platform (looked in {path})"
        )
    spec = importlib.util.spec_from_file_location(f"vendored_{block_id}", path)
    if spec is None or spec.loader is None:
        raise BlockNotVendored(f"{block_id}: vendored module has no loader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _CACHE[block_id] = module
    return module


def _load_failure(block_id: str) -> Optional[str]:
    """Reason the vendored module for *block_id* cannot be imported, if any."""
    if block_id in _CACHE:
        return None
    if block_id in _LOAD_FAILURES:
        return _LOAD_FAILURES[block_id]
    try:
        load_block(block_id)
        return None
    except BlockNotVendored as exc:
        _LOAD_FAILURES[block_id] = str(exc)
        return _LOAD_FAILURES[block_id]
    except Exception as exc:  # SyntaxError / ImportError / OSError from the slice
        _LOAD_FAILURES[block_id] = f"{type(exc).__name__}: {exc}"
        return _LOAD_FAILURES[block_id]


def _force_utf8_stdio() -> None:
    """Vendored blocks print progress; a non-UTF-8 stdout kills them mid-run."""
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


def _failed_steps(result: Dict[str, Any]) -> list:
    steps = result.get("results")
    if not isinstance(steps, list):
        return []
    failed = []
    for step in steps:
        if isinstance(step, dict) and str(step.get("status") or "").lower() in _FAILED_STATUSES:
            failed.append(step)
    return failed


def _run_shim(
    block_id: str,
    data: Dict[str, Any],
    action: Optional[str],
    params: Optional[Dict[str, Any]],
    reason: str,
) -> Dict[str, Any]:
    """Run the labelled offline implementation for *block_id*."""
    from app.offline_blocks import shim_for

    shim = shim_for(block_id)
    if shim is None:
        return _error_envelope(
            block_id, action, f"vendored block unavailable: {reason}"
        )
    try:
        answer = shim(data, action=action, params=params)
    except Exception as exc:  # noqa: BLE001 -- shim refusal is data
        return _error_envelope(block_id, action, f"{type(exc).__name__}: {exc}")
    if isinstance(answer, dict):
        answer.setdefault("block", block_id)
        answer.setdefault("action", action)
        answer.setdefault("vendored", False)
        answer.setdefault("vendoring_note", reason)
        status = str(answer.get("status") or "").lower()
        if status in _FAILED_STATUSES or answer.get("ok") is False:
            answer.setdefault("ok", False)
            answer["status"] = status if status in _FAILED_STATUSES else "error"
        return answer
    return {"block": block_id, "action": action, "status": "ok",
            "result": answer, "vendored": False}


def _error_envelope(block_id: str, action: Optional[str], error: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "status": "error",
        "block": block_id,
        "action": action,
        "error": error,
    }


def execute(
    block_id: str,
    payload: Dict[str, Any],
    action: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run a vendored block locally and return its result envelope.

    ``action`` is a keyword: blocks read their operation from ``params`` and a
    payload-embedded ``action`` key is a contract violation, not a fallback.
    """
    bid = str(block_id or "").strip()
    if not bid:
        return _error_envelope(str(block_id), action, "block id required")

    data = payload if isinstance(payload, dict) else (
        {} if payload is None else {"value": payload}
    )

    failure = _load_failure(bid)
    if failure is not None:
        return _run_shim(bid, data, action, params, failure)

    module = load_block(bid)
    run = getattr(module, "run", None)
    if run is None:
        return _error_envelope(bid, action, f"{bid} exposes no run() entry point")

    kwargs: Dict[str, Any] = dict(params or {})
    if action is not None:
        kwargs["action"] = action
    _force_utf8_stdio()
    try:
        result = run(input=data, **kwargs)
    except Exception as exc:  # noqa: BLE001 -- a block refusal is data
        # A vendored module that cannot be driven offline (import/syntax/
        # attribute failures of the vendoring itself) falls back to the
        # labelled offline implementation, and the answer says so. Blocks
        # with no shim keep the error envelope: a domain refusal is data.
        from app.offline_blocks import shim_for

        if shim_for(bid) is not None:
            return _run_shim(
                bid, data, action, params, f"{type(exc).__name__}: {exc}"
            )
        return _error_envelope(bid, action, f"{type(exc).__name__}: {exc}")

    if isinstance(result, dict):
        result.setdefault("block", bid)
        result.setdefault("action", action)
        result.setdefault("vendored", True)
        status = str(result.get("status") or "").lower()
        failed = _failed_steps(result)
        if status in _FAILED_STATUSES or result.get("ok") is False or failed:
            refused = dict(result)
            refused["ok"] = False
            refused["status"] = status if status in _FAILED_STATUSES else "error"
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
    return {"block": bid, "action": action, "status": "ok",
            "result": result, "vendored": True}


def block_is_available(block_id: str) -> bool:
    """True when the block can actually be *run* in this process.

    A wrapper module that imports is not enough: ``vendor/blocks/<id>/block.py``
    imports its wrapped Store module lazily inside ``run()``, so a missing
    runtime dependency (numpy for vector_search, PyYAML for document_engine)
    leaves the wrapper importable and the block unrunnable. Resolving the
    wrapped class here turns that into an honest answer — either the block runs,
    or a labelled offline shim really covers it.
    """
    from app.offline_blocks import shim_for

    if _load_failure(block_id) is None and _target_failure(block_id) is None:
        return True
    return shim_for(block_id) is not None


def _target_failure(block_id: str) -> Optional[str]:
    """Reason the wrapped Store class cannot be resolved, if any."""
    if block_id in _RESOLVE_FAILURES:
        return _RESOLVE_FAILURES[block_id]
    try:
        module = load_block(block_id)
    except Exception as exc:  # noqa: BLE001 - an import failure is the answer
        _RESOLVE_FAILURES[block_id] = f"{type(exc).__name__}: {exc}"
        return _RESOLVE_FAILURES[block_id]
    getter = getattr(module, "get_block", None)
    if not callable(getter):
        return None
    try:
        getter(block_id)
    except Exception as exc:  # noqa: BLE001
        _RESOLVE_FAILURES[block_id] = f"{type(exc).__name__}: {exc}"
        return _RESOLVE_FAILURES[block_id]
    _RESOLVE_FAILURES.pop(block_id, None)
    return None
