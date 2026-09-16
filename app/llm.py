"""LLM access for VetClinicOS — offline by posture, loud when unconfigured.

Written by the factory WRITER role (codewhale exec).

The delivered platform runs with no outbound HTTP (posture P1). That makes
two behaviours non-negotiable, and both are implemented here rather than
papered over:

* **No credential → fail loud.** ``complete()`` raises
  :class:`MissingCredentialError` naming the environment variable. A
  summariser that silently returns "" is the stub this refuses to be.
* **Credential present but posture offline → fail loud too.**
  :class:`NetworkPostureRefused` says a provider call is not available in a
  delivered platform. Nothing here opens a socket.

What the platform *does* offer with no provider at all is a real, local
extractive summariser (:func:`summarize`) and the clinic's own corpus
(app.retrieval). Answers built that way are labelled ``extractive`` so no
caller mistakes them for a model's judgement.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Sequence

PROVIDER_ENV = "VETCLINIC_LLM_PROVIDER"
LEGACY_PROVIDER_ENV = "CEREBRUM_LLM_PROVIDER"
API_KEY_ENV = "VETCLINIC_LLM_API_KEY"

_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")


class LLMError(RuntimeError):
    """Base class for LLM-layer refusals."""


class MissingCredentialError(LLMError):
    """No provider credential is configured: refuse rather than pretend."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(
            detail
            or (
                "no LLM provider credential: set %s (and %s) to enable a provider"
                % (PROVIDER_ENV, API_KEY_ENV)
            )
        )


class NetworkPostureRefused(LLMError):
    """The platform is offline by posture; a provider call is not available."""

    def __init__(self, provider: str = "") -> None:
        super().__init__(
            "posture P1: outbound HTTP is not available in a delivered platform"
            + (" (provider %r configured)" % provider if provider else "")
        )


def provider() -> str:
    return (
        os.getenv(PROVIDER_ENV) or os.getenv(LEGACY_PROVIDER_ENV) or ""
    ).strip().lower()


def api_key() -> str:
    return (os.getenv(API_KEY_ENV) or "").strip()


def provider_configured() -> bool:
    return bool(provider() and api_key())


def complete(prompt: str, *, max_tokens: int = 512) -> Dict[str, Any]:
    """Ask a provider. Raises loudly when it cannot be done honestly."""
    if not provider() or not api_key():
        raise MissingCredentialError()
    raise NetworkPostureRefused(provider())


def _split_sentences(text: str) -> List[str]:
    return [part.strip() for part in _SENTENCE_RE.findall(str(text or "")) if part.strip()]


def summarize(text: str, *, max_sentences: int = 3) -> Dict[str, Any]:
    """Deterministic local summary: the densest sentences, in order.

    Extractive, not generative — it never writes a sentence that was not in
    the input, which is the only honest summary an offline platform can give.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return {
            "summary": "",
            "sentences": 0,
            "method": "extractive",
            "provider": provider() or None,
        }
    words = [len(sentence.split()) for sentence in sentences]
    total_words = sum(words) or 1
    scored = sorted(
        range(len(sentences)),
        key=lambda index: (-words[index], index),
    )[: max(1, max_sentences)]
    chosen = sorted(scored)
    summary = " ".join(sentences[index] for index in chosen)
    return {
        "summary": summary,
        "sentences": len(chosen),
        "method": "extractive",
        "coverage": round(sum(words[index] for index in chosen) / total_words, 4),
        "provider": provider() or None,
    }


def status() -> Dict[str, Any]:
    configured = provider_configured()
    return {
        "provider": provider() or None,
        "credential_env": API_KEY_ENV,
        "configured": configured,
        "online": False,
        "posture": "P1 (no outbound HTTP)",
        "offline_summarizer": "extractive",
        "detail": (
            "provider configured but posture refuses outbound calls"
            if configured
            else "no provider credential: summarise() stays extractive and complete() raises MissingCredentialError"
        ),
    }
