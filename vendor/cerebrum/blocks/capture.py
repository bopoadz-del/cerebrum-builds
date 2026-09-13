"""Capture block — P1 local/scripted extract. Binds vendor/blocks/capture."""

from __future__ import annotations

from typing import Any, Dict

from vendor.cerebrum.core.universal_base import UniversalBlock


class CaptureBlock(UniversalBlock):
    """Offline capture: scripted text extract or local tesseract OCR."""

    name = "capture"
    version = "1.0.0"
    description = "P1 local/scripted OCR and scripted structure"
    layer = 3
    tags = ["capture", "ocr", "vision"]
    requires = []

    async def process(self, input_data: Any, params: Dict = None) -> Dict:
        params = params or {}
        action = params.get("action") or (
            input_data.get("action") if isinstance(input_data, dict) else None
        ) or "extract"
        if action not in {"extract", "capture", "structure", "ocr"}:
            return {"status": "error", "error": f"Unknown action: {action}"}
        from vendor.blocks.capture.block import run

        payload = input_data if isinstance(input_data, dict) else {"text": str(input_data or "")}
        structured = run(input=payload)
        return {"status": "success", **structured}
