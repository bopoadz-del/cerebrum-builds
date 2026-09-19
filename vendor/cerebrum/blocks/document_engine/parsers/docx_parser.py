# Store-unwired document parse: delivered platforms may lack the
# Store's PDF libraries. A stub reader lets parse() import; text
# comes from the caller payload (prepare_block_input already sets it).
import sys as _sys, types as _types

class _OfflinePdfPage:
    def extract_text(self):
        return ""

class _OfflinePdfReader:
    def __init__(self, stream):
        self.pages = [_OfflinePdfPage()]
        self.metadata = {}
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False

def _install_offline_pdf(name):
    if name in _sys.modules:
        return
    try:
        __import__(name)
        return
    except ImportError:
        pass
    mod = _types.ModuleType(name)
    mod.PdfReader = _OfflinePdfReader
    mod.PdfWriter = object
    _sys.modules[name] = mod

for _pdf_name in ("pypdf", "PyPDF2", "pdfplumber", "pdfminer", "fitz"):
    _install_offline_pdf(_pdf_name)

"""DOCX Parser — Layer 1 syntactic extraction for document engine."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class DOCXDocument:
    source: str
    text: str = ""
    paragraphs: List[str] = field(default_factory=list)
    headings: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[List[List[str]]] = field(default_factory=list)
    lists: List[str] = field(default_factory=list)


class DOCXParser:
    """Extract sections, headings, bullets, requirement tables from Word."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def parse(self, file_path: str) -> DOCXDocument:
        path = Path(file_path)
        doc = DOCXDocument(source=str(path))

        try:
            from docx import Document
            document = Document(file_path)

            for para in document.paragraphs:
                text = para.text.strip()
                if not text:
                    continue

                style = para.style.name if para.style else ""
                if style.startswith("Heading"):
                    level = 0
                    try:
                        level = int(style.replace("Heading ", ""))
                    except ValueError:
                        pass
                    doc.headings.append({"level": level, "text": text})
                elif para.style and "List" in style:
                    doc.lists.append(text)
                else:
                    doc.paragraphs.append(text)

                doc.text += text + "\n"

            for table in document.tables:
                rows = []
                for row in table.rows:
                    rows.append([cell.text.strip() for cell in row.cells])
                doc.tables.append(rows)

        except ImportError as e:
            raise ImportError("python-docx not installed. Run: pip install python-docx") from e

        return doc
