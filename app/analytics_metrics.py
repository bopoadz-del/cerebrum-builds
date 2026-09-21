"""Campaign outcome metrics: attempted, answered, interest split, transfers, conversion.

Written by the factory WRITER role (codewhale exec)

Layer 4 of CallOps: the numbers a brokerage manager actually asks for, read
back from the ledger every call event was already written to. This module is
a read model, not a second source of truth -- it aggregates
``outcome_capture_and_ledger`` rows (the capability whose contract writes one
event per call: attempt, answer, outcome, transfer, disposition) and computes
nothing the calls did not record.

Per campaign, and for the tenant that owns the rows:

    attempted          distinct calls with an ``attempt`` event
    answered           distinct calls with an ``answer`` event
    answered_rate      answered / attempted
    interest           the three-outcome split -- project_interested,
                       other_re_interested, not_interested -- counted per call
    qualified          distinct calls whose outcome is project_interested
    transfers          distinct calls with a ``transfer`` event
    conversion         app.formulas.conversion_rate(attempted, transfers)
                       -- transfers per attempted call, the customer's own
                       definition, so the metric is not re-invented here

Every number is labelled with the precedence.v1 layer it came from
(``formulas``): a computed result is layer 3, and an operator reading the
dashboard can see that this is arithmetic over their own ledger rather than a
model's recollection. A campaign name that appears on no row is reported with
zero counts rather than silently dropped, so "we ran it and nothing happened"
and "we never ran it" never look the same.

Campaign attribution comes from the ledger row's own ``campaign`` column. A
row that carries none is grouped under ``unattributed``: the platform does not
invent a campaign name to make the totals look complete.

Scope
-----
READS  ledger rows handed in by the caller (the route reads them from
       app.store scoped to the authenticated tenant); app.formulas (the
       conversion / percentage arithmetic); app.authority (the label).
WRITES nothing. A read model writes no row -- the calls already wrote them.
NEVER  a second store, a second ledger, or a table of its own; another
       tenant's rows; a campaign name invented for a row that has none.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from app import authority, formulas

#: The three-outcome vocabulary, as schema (app/models.py CONSTRAINTS carries
#: the same list -- tests/test_campaign_metrics.py asserts the two agree, so
#: this is a read of the contract, not a second declaration of it).
OUTCOMES: Sequence[str] = ("project_interested", "other_re_interested", "not_interested")

#: Ledger event types this read model knows how to count.
ATTEMPT = "attempt"
ANSWER = "answer"
OUTCOME = "outcome"
TRANSFER = "transfer"
DISPOSITION = "disposition"

UNATTRIBUTED = "unattributed"

#: A computed metric is layer 3 of precedence.v1.
METRIC_LAYER = "formulas"


class MetricsRefused(ValueError):
    """The caller asked for something the ledger cannot answer."""


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _campaign_of(row: Dict[str, Any]) -> str:
    return _text(row.get("campaign")) or UNATTRIBUTED


def _call_key(row: Dict[str, Any], index: int) -> str:
    """The call a ledger row belongs to.

    ``call_sid`` is the platform's own key (the carrier's SID where Twilio
    supplied one, the record's reference otherwise). A row with neither is
    still counted, keyed by its own ledger position, so a malformed row
    cannot silently vanish from the attempted count.
    """
    key = _text(row.get("call_sid")) or _text(row.get("reference"))
    return key or "row:%d" % index


class _Bucket:
    """One campaign's distinct calls and events."""

    def __init__(self, campaign: str) -> None:
        self.campaign = campaign
        self.attempts: set = set()
        self.answers: set = set()
        self.transfers: set = set()
        self.dispositions: set = set()
        self.outcomes: Dict[str, set] = {name: set() for name in OUTCOMES}
        self.unmapped_outcomes: Dict[str, set] = {}
        self.ledger_events = 0

    def add(self, row: Dict[str, Any], index: int) -> None:
        self.ledger_events += 1
        event = _text(row.get("event_type")).lower()
        call = _call_key(row, index)
        if event == ATTEMPT:
            self.attempts.add(call)
        elif event == ANSWER:
            self.answers.add(call)
        elif event == TRANSFER:
            self.transfers.add(call)
        elif event == DISPOSITION:
            self.dispositions.add(call)
        elif event == OUTCOME:
            outcome = _text(row.get("outcome"))
            if outcome in self.outcomes:
                self.outcomes[outcome].add(call)
            else:
                # The route refuses an out-of-vocabulary outcome (422), so
                # this is a row written by something else. It is reported by
                # name rather than folded into one of the three: an unknown
                # outcome is not evidence of interest.
                self.unmapped_outcomes.setdefault(outcome or "(empty)", set()).add(call)

    def counts(self) -> Dict[str, Any]:
        attempted = len(self.attempts)
        answered = len(self.answers)
        transfers = len(self.transfers)
        interest = {name: len(self.outcomes[name]) for name in OUTCOMES}
        qualified = interest["project_interested"]
        return {
            "campaign": self.campaign,
            "attempted": attempted,
            "answered": answered,
            "answered_rate": formulas.percent_of(answered, attempted),
            "interest": interest,
            "qualified": qualified,
            "other_re_interested": interest["other_re_interested"],
            "not_interested": interest["not_interested"],
            "transfers": transfers,
            "transfer_rate": formulas.percent_of(transfers, answered),
            "conversion": formulas.conversion_rate(attempted, transfers),
            # Named bases, so a manager reading two percentages knows what
            # each one is a percentage *of* rather than assuming.
            "bases": {
                "answered_rate": "answered/attempted",
                "transfer_rate": "transfers/answered",
                "conversion": "transfers/attempted",
                "interest": "distinct calls per outcome",
            },
            "dispositions": len(self.dispositions),
            "ledger_events": self.ledger_events,
            "unmapped_outcomes": {
                name: len(calls) for name, calls in sorted(self.unmapped_outcomes.items())
            },
        }


def campaign_metrics(
    rows: Iterable[Dict[str, Any]],
    *,
    campaign: Optional[str] = None,
) -> Dict[str, Any]:
    """Aggregate ledger rows into the per-campaign metric list.

    ``rows`` are the tenant's ``outcome_capture_and_ledger`` rows, as returned
    by ``app.store.list_all``. Passing ``campaign`` narrows the answer to that
    one campaign; a campaign with no rows answers with zeros rather than an
    empty result, because "none ran" is the answer to the question asked.
    """
    wanted = _text(campaign)
    buckets: Dict[str, _Bucket] = {}
    ordered: List[str] = []
    index = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        index += 1
        name = _campaign_of(row)
        if wanted and name != wanted:
            continue
        bucket = buckets.get(name)
        if bucket is None:
            bucket = buckets[name] = _Bucket(name)
            ordered.append(name)
        bucket.add(row, index)

    if wanted and wanted not in buckets:
        buckets[wanted] = _Bucket(wanted)
        ordered.append(wanted)

    campaigns = [buckets[name].counts() for name in sorted(ordered)]
    totals = _totals(campaigns)
    envelope = authority.label_answer(
        METRIC_LAYER,
        [
            {"claim": "metric_source", "value": "outcome_capture_and_ledger"},
            {"claim": "metric_basis", "value": "distinct calls per event type"},
            {"claim": "conversion_basis", "value": "transfers/attempted (app.formulas.conversion_rate)"},
            {"claim": "campaign_filter", "value": wanted or "all"},
        ],
    )
    return {
        "ok": True,
        "campaign_filter": wanted or None,
        "campaigns": campaigns,
        "totals": totals,
        **envelope,
    }


def _totals(campaigns: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    attempted = sum(int(item.get("attempted") or 0) for item in campaigns)
    answered = sum(int(item.get("answered") or 0) for item in campaigns)
    transfers = sum(int(item.get("transfers") or 0) for item in campaigns)
    interest = {
        name: sum(int((item.get("interest") or {}).get(name) or 0) for item in campaigns)
        for name in OUTCOMES
    }
    return {
        "campaigns": len(campaigns),
        "attempted": attempted,
        "answered": answered,
        "answered_rate": formulas.percent_of(answered, attempted),
        "interest": interest,
        "qualified": interest["project_interested"],
        "transfers": transfers,
        "transfer_rate": formulas.percent_of(transfers, answered),
        "conversion": formulas.conversion_rate(attempted, transfers),
    }


def metric_names() -> List[str]:
    """The metric list the brief named, in the order the desk renders it."""
    return [
        "attempted",
        "answered",
        "answered_rate",
        "interest",
        "transfers",
        "conversion",
    ]
