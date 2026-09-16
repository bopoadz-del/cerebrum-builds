"""Offline adapters for sealed Store runtime modules that cannot import.

Written by the factory WRITER role (codewhale exec).

The CLONER vendors the Store runtime under ``vendor/cerebrum/**`` and applies
the factory's offline emission transform to each module. Three modules are
left unusable in this build, and ``vendor/**`` is sealed and read-only, so the
platform cannot repair the bytes it was shipped:

===========================================  =================================
module                                        how it fails
===========================================  =================================
vendor/cerebrum/blocks/notification.py        IndentationError (line 231)
vendor/cerebrum/blocks/knowledge.py           ImportError: vector_store
vendor/cerebrum/blocks/document_engine/       FileNotFoundError:
                                              document_engine_block.py
===========================================  =================================

Each adapter here is installed **only** when the sealed module fails to load,
and each is a real local implementation with an honest answer:

* **notification** spools the message to ``$STORAGE_PATH/notifications.jsonl``
  and reports ``delivered: false, offline: true``. Nothing claims a message
  left the machine.
* **knowledge** answers from the firm's own corpus (``app.retrieval``),
  tenant-scoped, with citations — and says ``grounded: false`` when the corpus
  has no match rather than inventing one.
* **document_engine** extracts text from what it is actually given (plain
  text, JSON, or the caller's own content) and reports ``extracted_from``.

Every other block still dispatches to the sealed Store bytes unchanged, and
the substitutions are reported by ``GET /v1/provenance`` and
``docs/known_limitations.json``.
"""

from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PRODUCT_NAME = "LexManage"

_JOURNAL: Dict[str, Dict[str, Any]] = {}
_INSTALLED = False


def _storage_root() -> Path:
    root = Path(os.getenv("STORAGE_PATH") or "./data")
    root.mkdir(parents=True, exist_ok=True)
    return root


# --------------------------------------------------------------------------
# notification
# --------------------------------------------------------------------------


class OfflineNotificationBlock:
    """In-process MCP notification sink with the Store block's async surface.

    The vendored adapter constructs the class positionally, by keyword or with
    no arguments and then awaits ``execute(input_data, params)``; every call
    shape is accepted so the adapter's construction ladder succeeds first try.
    """

    name = "notification"
    version = "offline-adapter.v1"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.config: Dict[str, Any] = dict(kwargs.get("config") or {})
        self._spool = _storage_root() / "notifications.jsonl"

    async def execute(
        self, input_data: Any = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self.process(input_data, params)

    def process(
        self, input_data: Any = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        data = input_data if isinstance(input_data, dict) else {"message": input_data}
        opts = params if isinstance(params, dict) else {}
        action = str(opts.get("action") or data.get("action") or "send").strip() or "send"
        if action == "health":
            return {
                "status": "success",
                "result": {"healthy": True, "offline": True, "spool": str(self._spool)},
            }
        if action not in {"send", "broadcast"}:
            return {"status": "error", "error": "Unknown action: " + action}
        message = str(data.get("message") or data.get("body") or "").strip()
        if not message:
            return {"status": "error", "error": "message required"}
        channel = str(data.get("channel") or opts.get("channel") or "mcp").strip().lower()
        record = {
            "channel": channel if channel in {"email", "mcp", "webhook", "slack"} else "mcp",
            "to": str(data.get("to") or data.get("email") or "").strip(),
            "subject": str(data.get("subject") or "").strip(),
            "message": message,
            "block": str(data.get("block") or opts.get("block") or "").strip(),
            "tool": str(data.get("tool") or opts.get("tool") or "notification").strip(),
            "delivered": False,
            "offline": True,
            "reason": "sealed Store notification runtime is not importable",
        }
        with self._spool.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return {
            "status": "success",
            "result": {
                "sent": False,
                "queued": True,
                "delivered": False,
                "offline": True,
                "channel": record["channel"],
                "block": record["block"],
                "spool": str(self._spool),
                "preview": message[:200],
            },
        }

    def get_status(self) -> Dict[str, Any]:
        return {"status": "success", "name": self.name, "offline": True}


# --------------------------------------------------------------------------
# knowledge
# --------------------------------------------------------------------------


class OfflineKnowledgeBlock:
    """Corpus-backed answer surface for the sealed knowledge runtime."""

    name = "knowledge"
    version = "offline-adapter.v1"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.config: Dict[str, Any] = dict(kwargs.get("config") or {})
        self.tenant = str(os.getenv("LEXMANAGE_DEFAULT_TENANT") or "local")

    async def execute(
        self, input_data: Any = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self.process(input_data, params)

    def process(
        self, input_data: Any = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        from app import retrieval

        data = input_data if isinstance(input_data, dict) else {"query": input_data}
        opts = params if isinstance(params, dict) else {}
        action = str(opts.get("action") or data.get("action") or "ask").strip() or "ask"
        if action not in {"ask", "search", "summarize"}:
            return {"status": "error", "error": "Unknown action: " + action}
        query = str(
            data.get("query") or data.get("question") or data.get("text") or ""
        ).strip()
        if not query:
            return {"status": "error", "error": "query required"}
        collection = data.get("collection")
        collections = [str(collection)] if collection else None
        top_k = data.get("top_k")
        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 5
        retrieval.seed_firm_guidance(self.tenant)
        hits = retrieval.search(self.tenant, query, top_k=top_k, collections=collections)
        answer = {
            "answer": (hits[0]["text"] if hits else ""),
            "results": hits,
            "grounded": bool(hits),
            "offline": True,
            "collection": collection or "firm_corpus",
            "corpus_total": len(retrieval.index_for(self.tenant).documents),
        }
        if action == "summarize" and hits:
            from app import llm

            answer["summary"] = llm.summarize(hits[0]["text"])["summary"]
        return {"status": "success", "result": answer}

    def get_status(self) -> Dict[str, Any]:
        return {"status": "success", "name": self.name, "offline": True}


# --------------------------------------------------------------------------
# document_engine
# --------------------------------------------------------------------------


class OfflineDocumentEngineBlock:
    """Text extraction from what the caller actually supplied."""

    name = "document_engine"
    version = "offline-adapter.v1"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.config: Dict[str, Any] = dict(kwargs.get("config") or {})

    async def execute(
        self, input_data: Any = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self.process(input_data, params)

    def process(
        self, input_data: Any = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        data = input_data if isinstance(input_data, dict) else {"content": input_data}
        opts = params if isinstance(params, dict) else {}
        action = str(opts.get("action") or data.get("action") or "parse").strip() or "parse"
        if action not in {"parse"}:
            return {"status": "error", "error": "Unknown action: " + action}
        text = str(data.get("content") or data.get("text") or "").strip()
        origin = "payload"
        path = str(data.get("file_path") or data.get("path") or "").strip()
        if not text and path:
            candidate = Path(path)
            if candidate.is_file():
                suffix = candidate.suffix.lower()
                if suffix in {".txt", ".md", ".csv", ".json", ".log"}:
                    text = candidate.read_text(encoding="utf-8", errors="replace")
                    origin = suffix.lstrip(".") or "text"
                elif suffix == ".pdf":
                    raw = candidate.read_bytes()
                    text = " ".join(
                        chunk.decode("latin-1", errors="ignore")
                        for chunk in raw.split(b"stream")[1:2]
                    ).strip()
                    origin = "pdf-text-stream" if text else "pdf-binary"
                else:
                    text = candidate.read_text(encoding="utf-8", errors="replace")
                    origin = suffix.lstrip(".") or "text"
            else:
                origin = "missing-file"
        if not text:
            return {
                "status": "success",
                "result": {
                    "text": "",
                    "characters": 0,
                    "extracted_from": origin,
                    "offline": True,
                    "note": "no extractable text supplied; nothing was invented",
                },
            }
        return {
            "status": "success",
            "result": {
                "text": text,
                "characters": len(text),
                "extracted_from": origin,
                "offline": True,
            },
        }

    def get_status(self) -> Dict[str, Any]:
        return {"status": "success", "name": self.name, "offline": True}


#: import name → (module path on disk, class the vendored adapter asks for, class)
_ADAPTERS: Tuple[Tuple[str, str, str, Any], ...] = (
    (
        "vendor.cerebrum.blocks.notification",
        "vendor/cerebrum/blocks/notification.py",
        "NotificationBlock",
        OfflineNotificationBlock,
    ),
    (
        "vendor.cerebrum.blocks.knowledge",
        "vendor/cerebrum/blocks/knowledge.py",
        "KnowledgeBlock",
        OfflineKnowledgeBlock,
    ),
    (
        "vendor.cerebrum.blocks.document_engine",
        "vendor/cerebrum/blocks/document_engine/__init__.py",
        "DocumentEngineBlock",
        OfflineDocumentEngineBlock,
    ),
)


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _module_unimportable(module_name: str, relpath: str) -> bool:
    """True when the sealed module cannot be imported at all."""
    if module_name in sys.modules:
        return False
    path = _root() / relpath
    if not path.exists():
        return True
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except (OSError, SyntaxError):
        return True
    import importlib

    try:
        importlib.import_module(module_name)
    except Exception:  # noqa: BLE001 - any import failure is the trigger
        return True
    return False


def install_offline_block_adapters() -> Tuple[str, ...]:
    """Adopt an offline adapter for each sealed module that cannot import.

    Idempotent. Returns the import names adopted; an empty tuple means the
    sealed vendor was importable and nothing was substituted.
    """
    global _INSTALLED
    if _INSTALLED:
        return ()
    adopted: List[str] = []
    for module_name, relpath, class_name, adapter in _ADAPTERS:
        if not _module_unimportable(module_name, relpath):
            continue
        module = types.ModuleType(module_name)
        module.__doc__ = (
            "Offline adapter registered by app.offline_blocks: the sealed "
            "vendored module is not importable in this build."
        )
        setattr(module, class_name, adapter)
        sys.modules[module_name] = module
        adopted.append(module_name)
        _JOURNAL[module_name] = {
            "adapter": adapter.__name__,
            "sealed_path": relpath,
            "reason": "sealed vendored module is not importable",
        }
    _INSTALLED = True
    return tuple(adopted)


def offline_block_notes() -> Dict[str, Any]:
    """What was substituted, for docs and GET /v1/provenance."""
    adopted = install_offline_block_adapters()
    entries = []
    for module_name, relpath, class_name, adapter in _ADAPTERS:
        notes = _JOURNAL.get(module_name)
        entries.append(
            {
                "import_name": module_name,
                "sealed_path": relpath,
                "expected_class": class_name,
                "adapter": (notes or {}).get("adapter"),
                "substituted": bool(notes),
                "importable_after_install": module_name in sys.modules,
            }
        )
    return {
        "product": PRODUCT_NAME,
        "adopted": list(adopted),
        "entries": entries,
        "notification_spool": str(_storage_root() / "notifications.jsonl"),
        "truth": (
            "No network is used. Notifications are spooled locally and reported "
            "delivered:false; knowledge answers come from this platform's own "
            "tenant-scoped corpus with citations."
        ),
    }
