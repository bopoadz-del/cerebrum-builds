"""property_onboarding — new-asset template apply. REUSE spec_analyzer + recommendation_template."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import recommendation_template_input, spec_analyzer_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, file.input_document, env.process, config.runtime
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["spec_analyzer", "recommendation_template"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze onboarding specs and emit ranked recommendations for the new property."""
    blocks = {
        "spec_analyzer": execute(
            "spec_analyzer",
            spec_analyzer_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("spec_analyzer"),
        ),
        "recommendation_template": execute(
            "recommendation_template",
            recommendation_template_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("recommendation_template"),
        ),
    }
    return ok_envelope("property_onboarding", payload, blocks)
