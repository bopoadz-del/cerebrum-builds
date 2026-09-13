"""File Hasher Block — SHA-256 digest of constructed content. Offline only."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from vendor.cerebrum.core.universal_base import UniversalBlock


class FileHasherBlock(UniversalBlock):
    name = "file_hasher"
    version = "1.0.0"
    description = "Hash file or payload content for integrity"
    layer = 1
    tags = ["security", "integrity", "hash"]
    requires = []
    default_config = {"algorithm": "sha256"}
    ui_schema = {
        "input": {"type": "json", "placeholder": '{"content": "..."}', "multiline": True},
        "output": {"type": "json", "fields": [{"name": "digest", "type": "text"}]},
        "params": [
            {
                "name": "action",
                "type": "select",
                "options": ["hash", "verify", "digest"],
                "default": "hash",
            }
        ],
    }

    def __init__(self, hal_block=None, config: Dict = None):
        super().__init__(hal_block, config)

    async def process(self, input_data: Any, params: Dict = None) -> Dict:
        params = params or {}
        data = input_data if isinstance(input_data, dict) else {"content": input_data}
        action = params.get("action") or data.get("event_action") or "hash"
        if action in {"hash", "digest"}:
            return self._hash(data)
        if action == "verify":
            return self._verify(data)
        return {"error": f"Unknown action: {action}"}

    def _bytes(self, data: Dict[str, Any]) -> bytes:
        content = data.get("content")
        if content is None:
            content = data.get("text") or data.get("body") or data.get("filename") or data.get("result")
        if isinstance(content, bytes):
            return content
        if isinstance(content, dict):
            return json.dumps(content, default=str, sort_keys=True).encode()
        return str(content or "").encode()

    def _hash(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raw = self._bytes(data)
        digest = hashlib.sha256(raw).hexdigest()
        return {
            "hashed": True,
            "algorithm": "sha256",
            "digest": digest,
            "length": len(raw),
        }

    def _verify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        expected = str(data.get("expected") or data.get("digest") or "")
        actual = self._hash(data)["digest"]
        return {
            "verified": bool(expected) and expected == actual,
            "digest": actual,
            "algorithm": "sha256",
        }
