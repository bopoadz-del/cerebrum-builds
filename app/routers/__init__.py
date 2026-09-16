"""HTTP routers over the capability actions.

Written by the factory WRITER role (codewhale exec).

Lazy attribute access only: an eager re-export would import every router (and
through it app.routes) at package import time, which is the circular-import
class the writer gate refuses.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ["capabilities"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
