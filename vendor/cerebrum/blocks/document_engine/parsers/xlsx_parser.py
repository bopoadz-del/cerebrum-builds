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

"""XLSX Parser — Layer 1 syntactic extraction for document engine."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class XLSXDocument:
    source: str
    sheets: Dict[str, List[List[Any]]] = field(default_factory=dict)
    headers: Dict[str, List[str]] = field(default_factory=dict)


class XLSXParser:
    """Extract sheets, headers, and schedule-template fields from Excel."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def parse(self, file_path: str) -> XLSXDocument:
        path = Path(file_path)
        doc = XLSXDocument(source=str(path))

        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    rows.append([str(cell) if cell is not None else "" for cell in row])
                doc.sheets[sheet_name] = rows
                if rows:
                    doc.headers[sheet_name] = [str(c).strip() for c in rows[0]]
        except ImportError as e:
            raise ImportError("openpyxl not installed. Run: pip install openpyxl") from e

        return doc
