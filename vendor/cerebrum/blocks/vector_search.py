"""Vector Search Block — lexical offline search. No network corpus."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List

from vendor.cerebrum.core.universal_base import UniversalBlock


class VectorSearchBlock(UniversalBlock):
    name = "vector_search"
    version = "1.0.0"
    description = "Offline lexical search (Store operation default: search)"
    layer = 2
    tags = ["search", "retrieval", "offline"]
    requires = []
    default_config = {}
    ui_schema = {
        "input": {"type": "json", "placeholder": '{"query": "..."}', "multiline": True},
        "output": {"type": "json", "fields": [{"name": "results", "type": "json"}]},
        "params": [
            {
                "name": "action",
                "type": "select",
                "options": ["search", "index", "upsert"],
                "default": "search",
            }
        ],
    }

    def __init__(self, hal_block=None, config: Dict = None):
        super().__init__(hal_block, config)
        self._docs: List[Dict[str, Any]] = []

    async def process(self, input_data: Any, params: Dict = None) -> Dict:
        params = params or {}
        data = input_data if isinstance(input_data, dict) else {"query": str(input_data or "")}
        action = params.get("action") or params.get("operation") or "search"
        if action in {"index", "upsert"}:
            return self._index(data)
        if action == "search":
            return self._search(data, params)
        return {"error": f"Unknown action: {action}"}

    def _tokens(self, text: str) -> List[str]:
        return [t for t in re.findall(r"[a-z0-9]+", str(text).lower()) if t]

    def _index(self, data: Dict[str, Any]) -> Dict[str, Any]:
        text = str(data.get("text") or data.get("content") or data.get("query") or "")
        doc = {
            "id": data.get("doc_id") or data.get("reference") or f"doc-{len(self._docs)+1}",
            "text": text,
            "metadata": data.get("metadata") or {},
        }
        self._docs.append(doc)
        return {"indexed": True, "doc_id": doc["id"], "count": len(self._docs)}

    def _search(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        query = str(data.get("query") or data.get("question") or data.get("text") or "")
        if not query and isinstance(data.get("result"), dict):
            query = str(data["result"].get("summary") or "")
        n_results = int(params.get("n_results") or data.get("n_results") or 5)
        q = set(self._tokens(query))
        scored = []
        corpus = self._docs or [
            {
                "id": "safety-sms",
                "text": "Safety management system occurrence reporting and risk control.",
                "metadata": {"layer": "sms"},
            }
        ]
        for doc in corpus:
            d = self._tokens(doc.get("text", ""))
            if not q or not d:
                score = 0.0
            else:
                score = len(q.intersection(d)) / math.sqrt(len(q) * max(len(d), 1))
            scored.append({**doc, "score": round(score, 6)})
        scored.sort(key=lambda row: row["score"], reverse=True)
        hits = [row for row in scored if row["score"] > 0][:n_results]
        return {
            "status": "success",
            "results": hits,
            "total_found": len(hits),
            "query": query,
        }
