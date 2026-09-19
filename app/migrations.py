"""Alembic runner for the platform.

Written by the factory WRITER role (codewhale exec)

``upgrade_head()`` applies every revision to ``STORAGE_PATH/platform.db``. The
schema is versioned and owned here — ``app/store.py`` never creates a domain
table at connect time, so a missing revision is a deploy failure rather than a
silently created table.

Scope
-----
READS  ``alembic/``, ``STORAGE_PATH``.
WRITES the database (DDL).
NEVER  network, ``vendor/**``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = ROOT / "alembic.ini"


def _config():
    from alembic.config import Config

    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{root / 'platform.db'}")
    return cfg


def upgrade_head() -> None:
    from alembic import command

    command.upgrade(_config(), "head")


def upgrade_to(revision: str) -> Optional[str]:
    """Apply revisions up to *revision*; return the revision now current.

    Pinned, not ``head``: a drill about the v1 -> v2 transition must not be
    invalidated by a later revision this product authors.
    """
    from alembic import command

    command.upgrade(_config(), str(revision))
    return current_revision()


def downgrade(revision: str) -> Optional[str]:
    """Roll the schema back to *revision*; return the revision now current."""
    from alembic import command

    command.downgrade(_config(), str(revision))
    return current_revision()


def downgrade_base() -> None:
    from alembic import command

    command.downgrade(_config(), "base")


def head_revision() -> Optional[str]:
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(_config()).get_current_head()


def current_revision() -> Optional[str]:
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine

    from app import store

    engine = create_engine(f"sqlite:///{store.db_path()}")
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


if __name__ == "__main__":  # pragma: no cover - operator convenience
    upgrade_head()
    print("head:", head_revision())


#: Read-only register of the revisions this platform ships. The revisions
#: themselves live in ``alembic/versions/`` and are the source of truth.
REVISIONS: List[Dict[str, Any]] = [
    {
        "revision": "0001_baseline",
        "down_revision": None,
        "adds": ['stock_inventory_management', 'product_pricing', 'delivery_dispatch_tracking', 'fleet_cost_tracking', 'management_reporting_dashboard', 'user_roles_workforce', 'document_knowledge_qa', 'procedures_readiness_and_audit_trail'],
        "note": "one tenant-scoped table per capability entity (tenant_id column + index)",
    },
    {
        "revision": "0002_lifecycle_audit",
        "down_revision": "0001_baseline",
        "adds": ["lifecycle_audit", "work_queue", "idempotency_keys"],
        "note": "factory-written lifecycle audit substrate",
    },
]

