"""Capability router (the same object ``app/routes.py`` builds).

Written by the factory WRITER role (codewhale exec)

Included by ``app.main`` under the ``/v1`` prefix. Do not add a second router:
one contract, one set of paths.
"""

from __future__ import annotations

from app.routes import router

__all__ = ("router",)
