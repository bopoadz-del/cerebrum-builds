"""HTTP routes over the actions -- one router, re-exported.

Written by the factory WRITER role (codewhale exec)

The platform's entire HTTP surface is the single ``app.routes.router`` (the
factory kernel's shape, which the generated suites import). This package is a
real, importable handle on that same router so ``app.routers`` exists as the
platform layout documents; it is not a second API and it owns no routes of its
own.

Scope
-----
READS  app.routes (the one router).
WRITES nothing.
NEVER  network, ``vendor/**``, a second HTTP surface.
"""

from app.routes import router

__all__ = ["router"]
