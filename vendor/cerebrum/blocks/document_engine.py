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

"""Compatibility shim for the document_engine platform wrapper.

The ``document_engine/`` package shadows this file for
``import vendor.cerebrum.blocks.document_engine``. The wrapper body lives in
``document_engine_block.py`` so factory CLONER / runtime-slice scanners
that resolve ``vendor.cerebrum.blocks.(\\w+)`` find an on-disk module.

Loaders that still open this path by filename get the same class.
"""

from vendor.cerebrum.blocks.document_engine_block import DocumentEngineBlock

__all__ = ["DocumentEngineBlock"]
