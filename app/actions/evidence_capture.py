"""evidence_capture — capture supporting artifacts. REUSE capture (action=extract)."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import capture_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, file.input_image, env.process, config.runtime
# WRITES: caller.output, file.local.write
# NEVER: cloud LLM / Ollama

BLOCK_IDS = ["capture"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract scripted evidence from the domain record via the capture block."""
    blocks = {
        "capture": execute(
            "capture",
            capture_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("capture"),
        ),
    }
    return ok_envelope("evidence_capture", payload, blocks)
