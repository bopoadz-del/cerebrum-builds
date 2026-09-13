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

from .pdf_parser import PDFParser, PDFDocument
from .docx_parser import DOCXParser, DOCXDocument
from .xlsx_parser import XLSXParser, XLSXDocument

__all__ = [
    "PDFParser", "PDFDocument",
    "DOCXParser", "DOCXDocument",
    "XLSXParser", "XLSXDocument",
]
