"""The conversation brain: grounded turns, or no turn at all.

Two modes, same contract:

* **deterministic** (default, and the only mode CI runs): turns are built
  from retrieved project-sheet text and the fixed three-outcome vocabulary.
  No network, no weights, no invented numbers.
* **model** (when ``LLM_PROVIDER`` and ``LLM_API_KEY`` are set): a real
  completion request to the operator's endpoint, with the retrieved
  evidence in the prompt *and* a grounding check on the way out. A number
  the model produced that is not in the evidence is not spoken; the claim is
  withheld instead.

That second sentence is the whole point: a bot that improvises a handover
date is the liability this platform exists to avoid, so the model is told
what it may claim and is checked afterwards regardless.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Mapping, Optional, Sequence

from app import config, retrieval
from app.authority import Claim, envelope
from app.domain import OUTCOME_VOCABULARY, classify_outcome, collect_fields

NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

CLAIM_HINTS = {
    "price": ("price", "prices", "cost", "how much", "budget", "starting"),
    "payment_plan": ("payment", "plan", "instalment", "installment", "down payment"),
    "handover_date": ("handover", "delivery", "completion", "when is it ready"),
    "amenities": ("amenities", "pool", "gym", "parking", "facilities"),
    "location": ("location", "where is", "district", "how far"),
    "availability": ("available", "availability", "left", "remaining"),
}

WITHHELD_LINE = {
    "en": "I don't have that confirmed on the sheet I was given, so I won't guess "
    "— a broker will follow up with the exact figure.",
    "ar": "ليست لدي هذه المعلومة مؤكدة في المستند، ولن أخمّنها — سيتواصل معك الوسيط بالرقم الدقيق.",
}


def claim_type_for(text: str) -> Optional[str]:
    lowered = str(text or "").lower()
    for claim, hints in CLAIM_HINTS.items():
        if any(hint in lowered for hint in hints):
            return claim
    return None


def unsupported_claims(answer: str, evidence: Sequence[str]) -> List[str]:
    """Numbers in a draft answer that the evidence does not contain.

    This is the grounding check: it runs on the model's draft and on the
    deterministic planner's draft alike, so neither can introduce a figure
    retrieval did not supply.
    """
    haystack = " ".join(str(item or "") for item in evidence)
    haystack_numbers = {match.group(0) for match in NUMBER_RE.finditer(haystack)}
    haystack_years = {match.group(0) for match in YEAR_RE.finditer(haystack)}
    problems: List[str] = []
    for match in NUMBER_RE.finditer(str(answer or "")):
        token = match.group(0)
        if token in haystack_numbers:
            continue
        if "." in token and token.split(".")[0] in haystack_numbers:
            continue
        if token in haystack_years:
            continue
        digest = token.replace(",", "")
        if digest in {value.replace(",", "") for value in haystack_numbers}:
            continue
        problems.append(token)
    return problems


def _model_turn(
    *,
    question: str,
    evidence: Sequence[str],
    language: str,
    project_tag: str,
) -> Optional[str]:
    """One real completion request. Returns None when unavailable."""
    if not (config.LLM_PROVIDER and config.LLM_API_KEY):
        return None
    system = (
        "You are an outbound voice agent for a real-estate brokerage. Answer only "
        "from the EVIDENCE passages. If the evidence does not state a price, a "
        "payment plan or a handover date, say you will confirm it rather than "
        "guessing. Never invent a number. Reply in the caller's language."
    )
    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "project": project_tag,
                        "language": language,
                        "question": question,
                        "evidence": list(evidence),
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.0,
    }
    base = str(config.LLM_BASE_URL or "").rstrip("/")
    if not base.startswith(("https://", "http://")):
        return None
    request = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + str(config.LLM_API_KEY),
        },
        method="POST",
    )
    try:
        # nosec B310 - the base URL is checked to be http(s) immediately above.
        with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310 - http(s) checked above
            body = json.loads(response.read().decode("utf-8") or "{}")
    except (urllib.error.URLError, ValueError, OSError):
        return None
    choices = body.get("choices") or []
    if not choices:
        return None
    return str((choices[0].get("message") or {}).get("content") or "").strip() or None


def dialogue_turn(tenant_id: str, record: Mapping[str, Any]) -> Dict[str, Any]:
    """One assistant turn for the voice edge, grounded or withheld."""
    body = dict(record or {})
    language = str(body.get("language") or "en").lower()[:2]
    if language not in ("en", "ar"):
        language = "en"
    project_tag = str(body.get("project_tag") or "")
    utterance = str(body.get("utterance") or body.get("question") or "")
    claim = claim_type_for(utterance) or body.get("claim_type")
    answer_block: Dict[str, Any] = {
        "answer": None,
        "withheld": True,
        "citations": [],
        "authority": envelope([], withheld_claim=str(claim or "retrieval")),
    }
    if utterance and claim:
        answer_block = retrieval.grounded_answer(
            tenant_id,
            project_tag=project_tag,
            question=utterance,
            claim_type=str(claim),
            language=language,
        )
        evidence = [str(hit.get("text") or "") for hit in answer_block.get("hits", [])] if answer_block.get("hits") else []
        if not evidence:
            evidence = [str(answer_block.get("quote") or "")]
        draft = _model_turn(
            question=utterance,
            evidence=evidence,
            language=language,
            project_tag=project_tag,
        )
        mode = "deterministic"
        if draft:
            problems = unsupported_claims(draft, evidence)
            if problems:
                # The model produced a figure retrieval never supplied. The
                # claim is withheld, not spoken with a caveat.
                answer_block = dict(answer_block)
                answer_block["withheld"] = True
                answer_block["answer"] = None
                answer_block["model_rejected_claims"] = problems
                answer_block["authority"] = envelope(
                    [], withheld_claim=str(claim), refused="model produced ungrounded figures"
                )
            else:
                answer_block = dict(answer_block)
                answer_block["answer"] = draft
                answer_block["quote"] = draft
                mode = "model"
        answer_block["mode"] = mode
    classification = classify_outcome(utterance)
    collected = collect_fields(utterance, body)
    say = answer_block.get("answer") or WITHHELD_LINE[language]
    claims = [
        Claim(
            name=str(claim or "utterance"),
            value=answer_block.get("answer") or "withheld",
            layer=str((answer_block.get("authority") or {}).get("layer") or "procedures"),
            source=str((answer_block.get("authority") or {}).get("label") or "llm.deterministic"),
        )
    ]
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "call_sid": body.get("call_sid"),
        "language": language,
        "project_tag": project_tag,
        "utterance": utterance,
        "say": say,
        "answer": answer_block.get("answer"),
        "withheld": bool(answer_block.get("withheld")),
        "citations": list(answer_block.get("citations") or []),
        "claim_type": claim,
        "outcome": classification["outcome"],
        "outcome_confident": classification["confident"],
        "outcome_matched": classification["matched"],
        "vocabulary": list(OUTCOME_VOCABULARY),
        "collected": collected,
        "mode": answer_block.get("mode", "deterministic"),
        "authority": answer_block.get("authority") or envelope(claims),
    }
