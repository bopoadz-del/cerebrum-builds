"""HTTP routers for the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

The capability surface lives in ``app/routes.py`` (one router for the whole
product). ``app/routers/capabilities.py`` re-exports it so a caller that
expects a router package finds the same object rather than a second API.
"""

from __future__ import annotations
