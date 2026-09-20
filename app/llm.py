"""LLM surface for the FleetOps Back-Office Platform.

Written by the factory WRITER role (codewhale exec)

Scope
  READS   process environment (provider keys) and the caller's prompt.
  WRITES  the caller's answer envelope, or a refusal.
  NEVER   a network call. This platform ships offline: the delivered runtime
          makes no outbound HTTP, so an LLM-backed answer is only available
          when the operator wires a local provider AND sets the key. With no
          provider configured the call fails loud -- it never fabricates an
          answer and never pretends a model answered.

``nl_answer`` is the only entry point the platform's own code calls. It is
deliberately synchronous and key-gated so a misconfigured deployment is
visible in the response rather than in a log nobody reads.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

#: Recognised local providers -> the environment variable carrying the key.
PROVIDER_KEYS: Dict[str, str] = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": "",  # local daemon, no key
}


class LLMUnavailable(RuntimeError):
    """No provider is configured. Raised loudly, never answered around."""


def configured_provider() -> Optional[str]:
    """The first provider whose credential is present, else None."""
    for provider, env_name in PROVIDER_KEYS.items():
        if not env_name:
            if os.environ.get("OLLAMA_BASE_URL"):
                return provider
            continue
        if str(os.environ.get(env_name) or "").strip():
            return provider
    return None


def provider_status() -> Dict[str, Any]:
    """What this deployment can and cannot do, without calling anything."""
    provider = configured_provider()
    return {
        "provider": provider,
        "available": provider is not None,
        "network": "disabled",
        "env": {name: bool(os.environ.get(name)) for name in PROVIDER_KEYS.values() if name},
    }


def nl_answer(
    prompt: str,
    *,
    context: Optional[List[str]] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Answer from a configured provider, or refuse with the reason.

    The offline pilot path never reaches a provider, so the honest answer is a
    refusal that names the missing credential -- not a templated guess.
    """
    question = str(prompt or "").strip()
    if not question:
        raise LLMUnavailable("prompt is required")
    chosen = provider or configured_provider()
    if not chosen:
        raise LLMUnavailable(
            "no LLM provider configured (set DEEPSEEK_API_KEY, "
            "OPENROUTER_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_BASE_URL)"
        )
    raise LLMUnavailable(
        "provider %r is configured but this build ships with outbound network "
        "disabled; wire a local provider adapter to serve answers" % (chosen,)
    )
