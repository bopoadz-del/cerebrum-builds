"""Document Engine Block — parse constructed text. Offline only."""

from __future__ import annotations

from typing import Any, Dict, List

from vendor.cerebrum.core.universal_base import UniversalBlock


class DocumentEngineBlock(UniversalBlock):
    name = "document_engine"
    version = "1.0.0"
    description = "Parse and extract structured fields from documents"
    layer = 3
    tags = ["document", "parse", "ops"]
    requires = []
    default_config = {}
    ui_schema = {
        "input": {"type": "json", "placeholder": '{"content": "..."}', "multiline": True},
        "output": {"type": "json", "fields": [{"name": "sections", "type": "json"}]},
        "params": [
            {
                "name": "action",
                "type": "select",
                "options": ["parse", "extract", "summarize"],
                "default": "parse",
            }
        ],
    }

    def __init__(self, hal_block=None, config: Dict = None):
        super().__init__(hal_block, config)

    async def process(self, input_data: Any, params: Dict = None) -> Dict:
        params = params or {}
        data = input_data if isinstance(input_data, dict) else {"content": input_data}
        action = params.get("action") or "parse"
        text = self._text(data)
        if action == "parse":
            return self._parse(text, data)
        if action == "extract":
            return {"fields": {"reference": data.get("reference"), "text": text[:240]}, "extracted": True}
        if action == "summarize":
            return {"summary": text[:240], "length": len(text)}
        return {"error": f"Unknown action: {action}"}

    def _text(self, data: Dict[str, Any]) -> str:
        content = data.get("content") or data.get("text") or data.get("body")
        if content is None and isinstance(data.get("result"), dict):
            content = data["result"].get("summary")
        return str(content or "")

    def _parse(self, text: str, data: Dict[str, Any]) -> Dict[str, Any]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sections: List[Dict[str, str]] = [
            {"heading": f"section_{idx}", "text": line} for idx, line in enumerate(lines[:12], start=1)
        ]
        if not sections:
            sections = [{"heading": "body", "text": text or str(data.get("filename") or "empty")}]
        return {
            "parsed": True,
            "filename": data.get("filename") or "document",
            "sections": sections,
            "section_count": len(sections),
        }
