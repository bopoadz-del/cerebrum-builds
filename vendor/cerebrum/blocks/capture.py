"""Capture block wrapper. Binds the P1 vendor adapter (extract, no cloud LLM)."""

from __future__ import annotations

from typing import Any, Dict

from vendor.cerebrum.core.universal_base import UniversalBlock
from vendor.blocks.capture.block import run as capture_run


class CaptureBlock(UniversalBlock):
    name = "capture"
    version = "1.0.0"
    description = "P1 local/scripted capture. Cloud LLM keys unused."
    layer = 3
    tags = ["capture", "ocr", "offline"]
    requires = []

    async def process(self, input_data: Any, params: Dict = None) -> Dict:
        params = params or {}
        action = params.get("action")
        if action is None and isinstance(input_data, dict):
            action = input_data.get("action")
        if action not in {"extract", "structure"}:
            return {"status": "error", "error": f"Unknown action: {action}"}
        data = input_data if isinstance(input_data, dict) else {"text": str(input_data)}
        extracted = capture_run(input=data)
        return {"status": "success", **extracted}
