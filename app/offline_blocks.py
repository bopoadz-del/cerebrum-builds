"""Offline fallbacks for blocks whose vendored module cannot be imported.

Written by the factory WRITER role (codewhale exec)

Three Store blocks vendor a module that does not import standalone in a
factory-built platform (a build-time vendoring defect, recorded in
``blocks.lock.json`` and reproduced by ``scripts/acceptance.py``):

* ``document_engine``  — the vendored package imports a sibling module path
  that the runtime slice writes as a package, so the import fails;
* ``knowledge``        — the vendored module imports ``vector_store`` from the
  Store core, which is not part of the offline slice;
* ``notification``     — the vendored module has an empty ``try:`` body after
  the slice stripped its foreign ``app.dependencies`` import (SyntaxError).

``app/dispatch.py`` uses these implementations ONLY when
``importlib`` refuses the vendored module, and every answer they return is
marked ``vendored: false`` with the reason, so the product never claims a
Store call it did not make. Each implementation is real domain logic over
``STORAGE_PATH`` — no network, no LLM, no credential:

* document_engine — hashes and sections an ingredient statement or spec;
* knowledge       — tenant-scoped token-overlap retrieval over a local corpus;
* notification    — channel contract (mcp | email | webhook) with delivery
  recorded locally; email without ``to`` is refused, exactly as the Store
  block refuses it.

Scope
-----
READS  ``STORAGE_PATH`` (filesystem).
WRITES ``STORAGE_PATH`` (hashed documents, corpus index, delivery log).
NEVER  network, SMTP, HTTP, ``vendor/**``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_LOCK = threading.Lock()

_CHANNELS = ("mcp", "email", "webhook", "slack")


def _storage_root() -> Path:
    root = Path(os.environ.get("STORAGE_PATH") or ".").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _tokens(text: str) -> List[str]:
    return [part for part in re.findall(r"[a-z0-9]+", (text or "").lower()) if part]


# --------------------------------------------------------------------------
# document_engine
# --------------------------------------------------------------------------

def _document_engine(data: Dict[str, Any], action: Optional[str] = None,
                     params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    act = str(action or (params or {}).get("action") or "parse").lower()
    if act not in ("parse", "render", "extract", "summarize"):
        return {"status": "error", "error": f"Unknown action: {act}"}

    text = ""
    for key in ("text", "content", "spec_text", "raw_text", "body"):
        candidate = data.get(key)
        if isinstance(candidate, str) and candidate.strip():
            text = candidate.strip()
            break

    file_path = data.get("file_path") or data.get("path")
    if not text and isinstance(file_path, str) and file_path.strip():
        candidate_path = Path(file_path)
        if not candidate_path.is_absolute():
            candidate_path = _storage_root() / candidate_path
        if not candidate_path.is_file():
            return {"status": "error", "error": f"File not found: {candidate_path}"}
        text = candidate_path.read_text(encoding="utf-8", errors="replace").strip()

    if not text:
        return {
            "status": "error",
            "error": "Provide file_path or document text as input",
        }

    sections = [
        line.strip()
        for line in text.splitlines()
        if line.strip().endswith(":") or line.strip().startswith("#")
    ]
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    document_id = "doc-" + digest[:16]
    record = {
        "document_id": document_id,
        "sha256": digest,
        "text": text,
        "format": "text",
        "action": act,
        "title": str(data.get("title") or data.get("reference") or document_id),
    }
    with _LOCK:
        with (_storage_root() / "documents.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return {
        "status": "success",
        "document_id": document_id,
        "sha256": digest,
        "format": "text",
        "chunk_count": max(1, len(sections)),
        "sections": sections[:20],
        "char_count": len(text),
    }


# --------------------------------------------------------------------------
# knowledge
# --------------------------------------------------------------------------

def _knowledge_index() -> Path:
    return _storage_root() / "knowledge_corpus.jsonl"


def _knowledge_rows() -> List[Dict[str, Any]]:
    path = _knowledge_index()
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("text"):
                rows.append(row)
    return rows


def _knowledge_score(query: str, text: str) -> float:
    q = set(_tokens(query))
    if not q:
        return 0.0
    d = set(_tokens(text))
    if not d:
        return 0.0
    return len(q & d) / float(len(q))


def _knowledge(data: Dict[str, Any], action: Optional[str] = None,
               params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    act = str(action or (params or {}).get("action") or "ask").lower()
    if act not in ("ask", "search", "summarize", "store", "ingest"):
        return {"status": "error", "error": f"Unknown action: {act}"}

    documents = data.get("documents") or data.get("items") or []
    if act in ("store", "ingest"):
        if not isinstance(documents, list) or not documents:
            return {"status": "error", "error": "documents required to store"}
        stored = 0
        with _LOCK:
            with _knowledge_index().open("a", encoding="utf-8") as handle:
                for item in documents:
                    if not isinstance(item, dict):
                        continue
                    text = str(item.get("text") or item.get("content") or "")
                    if not text.strip():
                        continue
                    handle.write(json.dumps(
                        {
                            "doc_id": item.get("doc_id") or "doc-" + uuid.uuid4().hex[:12],
                            "title": item.get("title") or "",
                            "tenant_id": item.get("tenant_id") or "local",
                            "text": text,
                        },
                        sort_keys=True,
                    ) + "\n")
                    stored += 1
        return {"status": "success", "stored": stored, "source": "offline-corpus"}

    query = str(
        data.get("query") or data.get("question") or data.get("text") or ""
    ).strip()
    if not query:
        return {"status": "error", "error": "query required"}

    # A single document supplied inline is indexed for this answer only.
    inline: List[Dict[str, Any]] = []
    for item in documents if isinstance(documents, list) else []:
        if isinstance(item, dict) and item.get("text"):
            inline.append({"doc_id": item.get("doc_id") or "inline", "text": str(item["text"])})
    if isinstance(data.get("text"), str) and data.get("text").strip() and not inline:
        inline.append({"doc_id": "inline", "text": data["text"]})

    rows = inline + _knowledge_rows()
    tenant = str(data.get("tenant_id") or "local")
    hits: List[Dict[str, Any]] = []
    for row in rows:
        if str(row.get("tenant_id") or tenant) != tenant:
            continue
        score = _knowledge_score(query, str(row.get("text") or ""))
        if score <= 0:
            continue
        hits.append(
            {
                "doc_id": row.get("doc_id"),
                "title": row.get("title") or row.get("doc_id"),
                "score": round(score, 6),
                "excerpt": str(row.get("text"))[:280],
            }
        )
    hits.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    top = hits[:5]
    if not top:
        return {
            "status": "success",
            "answer": "",
            "hit_count": 0,
            "citations": [],
            "insufficiency": True,
            "source": "offline-corpus",
        }
    return {
        "status": "success",
        "answer": " ".join(hit["excerpt"] for hit in top[:2]),
        "hit_count": len(top),
        "citations": [hit["doc_id"] for hit in top],
        "hits": top,
        "insufficiency": False,
        "source": "offline-corpus",
    }


# --------------------------------------------------------------------------
# notification
# --------------------------------------------------------------------------

def _notification(data: Dict[str, Any], action: Optional[str] = None,
                  params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    act = str(action or (params or {}).get("action") or "send").lower()
    if act == "health":
        return {"status": "success", "healthy": True, "channel": "offline"}
    if act not in ("send", "broadcast"):
        return {"status": "error", "error": f"Unknown action: {act}"}

    channel = str(data.get("channel") or "").strip().lower()
    if not channel:
        return {
            "status": "error",
            "error": "channel required: one of mcp | email | webhook | slack",
        }
    if channel not in _CHANNELS:
        return {
            "status": "error",
            "error": f"unsupported channel {channel!r}: one of mcp | email | webhook | slack",
        }
    message = str(data.get("message") or data.get("body") or "").strip()
    if not message:
        return {"status": "error", "error": "message required"}

    if channel == "mcp":
        target = data.get("block") or data.get("tool")
        if not (isinstance(target, str) and target.strip()):
            return {"status": "error", "error": "block or tool name required for MCP channel"}
    if channel == "email":
        to = str(data.get("to") or data.get("email") or "").strip()
        if not to:
            return {"status": "error", "error": "to (email) required"}
    if channel == "webhook":
        url = data.get("url") or data.get("to")
        if not (isinstance(url, str) and url.startswith("http")):
            return {"status": "error", "error": "url required (set 'url' or pass an http(s) URL as 'to')"}

    record = {
        "delivery_id": "ntf-" + uuid.uuid4().hex[:12],
        "channel": channel,
        "to": data.get("to") or data.get("block") or data.get("tool") or "",
        "message": message[:2000],
    }
    with _LOCK:
        with (_storage_root() / "notifications.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return {
        "status": "success",
        "sent": True,
        "delivered": 1,
        "channel": channel,
        "delivery_id": record["delivery_id"],
        "transport": "local-outbox",
    }


_SHIMS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "document_engine": _document_engine,
    "knowledge": _knowledge,
    "notification": _notification,
}


def shim_for(block_id: str) -> Optional[Callable[..., Dict[str, Any]]]:
    """The offline implementation for *block_id*, or None."""
    return _SHIMS.get(str(block_id or "").strip())


def shimmed_block_ids() -> List[str]:
    return sorted(_SHIMS)
