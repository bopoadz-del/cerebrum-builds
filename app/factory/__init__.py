"""Provenance package shipped with the delivered platform.

Written by the factory WRITER role (codewhale exec).

The platform carries its own authorship accounting so STORE acceptance can
measure it from inside the built image, where the factory itself is not on
the path (``scripts/acceptance.py`` imports
``app.factory.build.authorship``).
"""

from __future__ import annotations

__all__ = ["build"]
