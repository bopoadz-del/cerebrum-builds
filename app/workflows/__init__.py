"""The CallOps call lifecycle: states, transitions and the call-window guard.

Written by the factory WRITER role (codewhale exec)

One lead, one call, one state machine:

    queued -> dialing -> answered -> pitched -> qualified -> transferred
                                     |             |
                                     v             v
                                  callback       closed

``callback`` is where a busy / no-answer / failed dial goes while attempts
remain (max three, spaced by app.formulas.dial_pacing); with the budget spent
the call closes instead. The configured call window is a GUARD on the
transition, not a label: a transition out of a state whose window is shut is
refused before any event is published.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

#: Every state the call lifecycle may hold, in the order a call reaches them.
STATES: tuple = (
    "queued",
    "dialing",
    "answered",
    "pitched",
    "qualified",
    "transferred",
    "callback",
    "closed",
)

INITIAL_STATE = "queued"
TERMINAL_STATES = ("transferred", "closed")

#: The default configured calling window (a setting the operator owns; the
#: brief named neither a country nor business hours).
DEFAULT_WINDOW = "09:00-18:00"

#: state -> the states reachable from it with the window OPEN.
TRANSITIONS: Dict[str, tuple] = {
    "queued": ("dialing", "closed"),
    "dialing": ("answered", "callback", "closed"),
    "answered": ("pitched", "callback", "closed"),
    "pitched": ("qualified", "callback", "closed"),
    "qualified": ("transferred", "closed"),
    "transferred": ("closed",),
    "callback": ("dialing", "closed"),
    "closed": (),
}

#: The event that carries each transition.
EVENTS: Dict[tuple, str] = {
    ("queued", "dialing"): "call.dialing",
    ("dialing", "answered"): "call.answered",
    ("dialing", "callback"): "call.failed",
    ("answered", "pitched"): "call.pitched",
    ("answered", "callback"): "call.no_answer",
    ("pitched", "qualified"): "call.qualified",
    ("pitched", "callback"): "call.callback",
    ("qualified", "transferred"): "call.transferred",
    ("callback", "dialing"): "call.retry",
}

#: Retry attempts a busy / no-answer / failed dial is allowed. The third
#: attempt spends the budget, so the fourth outcome closes the call.
MAX_ATTEMPTS = 3

#: States a call may only enter inside the configured window.
WINDOW_GUARDED = frozenset({"queued", "dialing", "callback"})


def is_terminal(state: str) -> bool:
    return str(state or "").strip().lower() in TERMINAL_STATES


def transitions_from(state: str) -> tuple:
    return TRANSITIONS.get(str(state or "").strip().lower(), ())


def next_state(
    current: str,
    *,
    window_open: bool = True,
    attempt_count: int = 0,
    requested: Optional[str] = None,
) -> Dict[str, Any]:
    """The one transition this call may take, or a named refusal.

    ``requested`` lets the caller name a target explicitly (a status callback
    says what happened). Without one the machine advances along the first
    legal edge.
    """
    state = str(current or "").strip().lower()
    if state not in TRANSITIONS:
        return {
            "allowed": False,
            "next_state": None,
            "event": "",
            "guard": "unknown_state",
            "reason": f"unknown call state {current!r}: expected one of "
                      + ", ".join(STATES),
        }
    options = TRANSITIONS[state]
    if not options:
        return {
            "allowed": False,
            "next_state": None,
            "event": "",
            "guard": "terminal_state",
            "reason": f"{state} is terminal: the call lifecycle is over",
        }
    target = str(requested or "").strip().lower() or options[0]
    if target not in options:
        return {
            "allowed": False,
            "next_state": None,
            "event": "",
            "guard": "illegal_transition",
            "reason": f"{state} -> {target} is not a legal transition; "
                      f"from {state} a call may go to " + ", ".join(options),
        }
    if not window_open and target in WINDOW_GUARDED:
        return {
            "allowed": False,
            "next_state": None,
            "event": "",
            "guard": "call_window_closed",
            "reason": f"the configured call window is closed: a call is not "
                      f"moved to {target} outside calling hours",
        }
    if target == "callback" and int(attempt_count or 0) >= MAX_ATTEMPTS:
        return {
            "allowed": True,
            "next_state": "closed",
            "event": EVENTS.get((state, target), f"call.{target}"),
            "guard": "attempt_budget_spent",
            "reason": f"{attempt_count} attempts spent of {MAX_ATTEMPTS}: the "
                      "call is closed instead of retried",
        }
    return {
        "allowed": True,
        "next_state": target,
        "event": EVENTS.get((state, target), f"call.{target}"),
        "guard": "call_window_open",
        "reason": "",
    }


def legal_path(start: str = INITIAL_STATE) -> List[str]:
    """One full path through the machine, for documentation and tests."""
    path = [start]
    state = start
    seen = {start}
    while True:
        options = TRANSITIONS.get(state, ())
        if not options:
            return path
        nxt = options[0]
        if nxt in seen:
            return path
        path.append(nxt)
        seen.add(nxt)
        state = nxt
