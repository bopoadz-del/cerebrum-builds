"""Backup / restore / retention for the single persistence root."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.store import db_path, reset_connection, storage_root


def backup_root() -> Path:
    raw = os.environ.get("BACKUP_DIR")
    if raw:
        return Path(raw)
    return storage_root() / "backups"


def list_backups() -> List[Path]:
    root = backup_root()
    if not root.is_dir():
        return []
    return sorted(root.glob("platform-*.db"))


def create_backup() -> Path:
    source = db_path()
    root = backup_root()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = root / f"platform-{stamp}.db"
    reset_connection()
    if source.is_file():
        shutil.copy2(source, archive)
    else:
        archive.write_bytes(b"")
    return archive


def wipe_database() -> None:
    reset_connection()
    path = db_path()
    if path.is_file():
        path.unlink()
    for extra in path.parent.glob("platform.db*"):
        if extra.is_file():
            extra.unlink()


def restore_backup(archive: Path) -> Path:
    reset_connection()
    target = db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive, target)
    return target


def prune_backups(keep: int = 3) -> List[Path]:
    archives = list_backups()
    if len(archives) <= keep:
        return []
    removed = archives[: len(archives) - keep]
    for path in removed:
        path.unlink(missing_ok=True)
    return removed
