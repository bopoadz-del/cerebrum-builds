"""Regulatory-document rendering for compliance_documentation.

Written by the factory WRITER role (codewhale exec)

The capability generates the document it files, so the bytes that get hashed
and audited are real: one deterministic text rendering per compliance record,
written under ``STORAGE_PATH/documents``. Nothing here talks to a block or a
network; ``file_hasher`` does the hashing and ``audit`` does the logging.

Scope
-----
READS  ``STORAGE_PATH``.
WRITES exactly ONE rendered document file per call (idempotent for the same
       record: the same reference and document type reuse the same path).
NEVER  network, ``vendor/**``, another capability's table, ``tests/**``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict

SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def documents_root() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data")).resolve() / "documents"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _slug(value: Any, fallback: str) -> str:
    text = SAFE.sub("-", str(value or "").strip()).strip("-")
    return text[:80] or fallback


def render(record: Dict[str, Any]) -> Dict[str, Any]:
    """Render one compliance document and return its path and byte size.

    The body is the record itself plus the regulatory framing the record
    type implies, so the artifact can be filed and audited as-is.
    """
    reference = _slug(record.get("reference"), "reference")
    doc_type = _slug(record.get("document_type"), "document")
    lines = [
        "AGRISPHERE COMPLIANCE DOCUMENT",
        "=" * 32,
        f"Reference        : {record.get('reference')}",
        f"Document type    : {record.get('document_type')}",
        f"Jurisdiction     : {record.get('jurisdiction')}",
        f"Issued           : {record.get('issued_date')}",
        f"Expires          : {record.get('expiry_date')}",
        f"Attachment       : {record.get('attachment_path')}",
        f"Status           : {record.get('status')}",
        "",
        "Record",
        "-" * 32,
        json.dumps(record, indent=2, sort_keys=True, default=str),
        "",
        "Retention        : 7 years (regulatory default)",
        "",
    ]
    path = documents_root() / f"{doc_type}-{reference}.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "file_path": str(path),
        "document_type": record.get("document_type"),
        "reference": record.get("reference"),
        "size_bytes": path.stat().st_size,
    }
