"""HTTP routes over the capability actions (one router, one surface).

Written by the factory WRITER role (codewhale exec)

The router itself is built in ``app.routes`` -- the kernel job routes
(``/v1/jobs``, ``/v1/catalog``, ``/v1/inventory``, ``/v1/capabilities``,
``/v1/gates``, ``/v1/provenance``), one POST/GET/GET-id/PUT/DELETE set per
capability, and the platform surfaces (vendor health, tenancy, corpus,
grounded answers, precedence, formulas, llm). This package is the
importable view of that one router; there is no second API.

Scope
-----
READS  nothing (import re-export).
WRITES nothing.
NEVER  a second router, a second persistence path.
"""

from __future__ import annotations

from app.routes import router

__all__ = ["router"]
