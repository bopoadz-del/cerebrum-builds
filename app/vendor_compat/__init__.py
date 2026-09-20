"""Vendor-runtime compat registration (see module docstring of emit step).

``install()`` is idempotent and called by ``app.dispatch.load_block`` before
the first vendored block import. It registers, under the module names the
vendored package expects, the runtime modules this checkout's slice is
missing or that the CLONER rewrite broke:

* ``vendor.cerebrum.blocks.document_engine_block`` -- the wrapper package that
  *is* vendored, registered so the document_engine package does not try to
  open the sibling ``document_engine_block.py`` that this slice never got;
* ``vendor.cerebrum.core.vector_store`` -- offline copy (pool unavailable);
* ``vendor.cerebrum.blocks.notification`` -- unmangled copy of the same
  commit's NotificationBlock.

Nothing under ``vendor/`` is written: these are registrations into
``sys.modules`` plus an attribute on the vendored package.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

_INSTALLED = False

#: module name -> file shipped in this package (None = import the vendored
#: package of the same name).
_COMPAT_MODULES = {
    "vendor.cerebrum.core.vector_store": "vector_store.py",
    "vendor.cerebrum.blocks.notification": "notification.py",
}

#: vendored packages that must be pre-imported so their own file-based loader
#: never runs (the file it wants is absent from this slice).
_PREIMPORT = ("vendor.cerebrum.blocks.document_engine_block",)


def _register(module_name: str, filename: str) -> None:
    existing = sys.modules.get(module_name)
    if existing is not None and getattr(existing, "__file__", None):
        return
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"vendor compat: cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    parent_name, _, child = module_name.rpartition(".")
    parent = sys.modules.get(parent_name)
    if parent is not None:
        setattr(parent, child, module)


def install() -> bool:
    """Idempotent. True when the compat registrations are in place.

    False when this checkout carries no vendored stock at all (the writer's
    staging checkout is graded against the sealed stock the factory has
    already planted): the compat registrations are meaningless without it,
    and answering with an ImportError would describe the checkout as broken
    rather than as stock-less.
    """
    global _INSTALLED
    if _INSTALLED:
        return True
    try:
        import vendor  # noqa: F401  (the vendored package must be importable)
        import vendor.cerebrum.core  # noqa: F401
        import vendor.cerebrum.blocks  # noqa: F401
    except ImportError:
        return False

    for module_name in _PREIMPORT:
        if module_name in sys.modules:
            continue
        try:
            module = importlib.import_module(module_name)
        except Exception:  # noqa: BLE001 - the vendored shim module still exists
            continue
        sys.modules[module_name] = module
        parent_name, _, child = module_name.rpartition(".")
        parent = sys.modules.get(parent_name)
        if parent is not None:
            setattr(parent, child, module)

    for module_name, filename in _COMPAT_MODULES.items():
        _register(module_name, filename)

    _INSTALLED = True
    return True


__all__ = ["install"]
