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

"""Document Engine block for Cerebrum-Blocks.

Provides Parse → Reason → Map pipeline for technical document intelligence.
"""
import importlib.util
import os
import sys
from .main import main, parse_all
from .reasoner import DocumentReasoner, ReasonedOutput
from .mapper import DocumentMapper, StructuredDocument

# The document_engine/ package shadows app/blocks/document_engine.py for
# ``import vendor.cerebrum.blocks.document_engine``. The platform wrapper lives in
# document_engine_block.py so factory CLONER / runtime-slice scanners that
# resolve vendor.cerebrum.blocks.(\w+) find an on-disk module. Load it explicitly and
# register it in sys.modules so ``import vendor.cerebrum.blocks.document_engine_block``
# and this re-export share one class object.

_BLOCK_MODULE_NAME = "vendor.cerebrum.blocks.document_engine_block"
_BLOCK_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "document_engine_block.py")
)
_BLOCK_PACKAGE_INIT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "document_engine_block", "__init__.py")
)
if _BLOCK_MODULE_NAME in sys.modules:
    _block_module = sys.modules[_BLOCK_MODULE_NAME]
elif os.path.isfile(_BLOCK_FILE_PATH):
    _spec = importlib.util.spec_from_file_location(_BLOCK_MODULE_NAME, _BLOCK_FILE_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(
            f"document_engine wrapper missing at {_BLOCK_FILE_PATH}"
        )
    _block_module = importlib.util.module_from_spec(_spec)
    sys.modules[_BLOCK_MODULE_NAME] = _block_module
    _spec.loader.exec_module(_block_module)
elif os.path.isfile(_BLOCK_PACKAGE_INIT):
    from vendor.cerebrum.blocks.document_engine_block import DocumentEngineBlock as _DEB

    class _Loaded:
        DocumentEngineBlock = _DEB

    _block_module = _Loaded()
else:
    raise ImportError(
        f"document_engine wrapper missing at {_BLOCK_FILE_PATH} or {_BLOCK_PACKAGE_INIT}"
    )
DocumentEngineBlock = _block_module.DocumentEngineBlock

__all__ = [
    "main",
    "parse_all",
    "DocumentReasoner",
    "ReasonedOutput",
    "DocumentMapper",
    "StructuredDocument",
    "DocumentEngineBlock",
]
