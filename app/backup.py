"""Backup / wipe / restore drills. Retention prunes oldest archives."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.store import db_path, reset_connection, storage_path


def backup_root() -> Path:
    raw = os.environ.get("BACKUP_DIR")
    if raw:
        return Path(raw).resolve()
    return (storage_path() / "backups").resolve()


def list_backups() -> List[Path]:
    root = backup_root()
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("platform-*.db") if p.is_file())


def create_backup() -> Path:
    reset_connection()
    root = backup_root()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = root / f"platform-{stamp}.db"
    src = db_path()
    if src.is_file():
        shutil.copy2(src, dest)
    else:
        dest.write_bytes(b"")
    return dest


def wipe_database() -> None:
    reset_connection()
    path = db_path()
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(path) + suffix) if suffix else path
        if candidate.exists():
            candidate.unlink()


def restore_backup(archive: Path) -> Path:
    reset_connection()
    dest = db_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive, dest)
    return dest


def prune_backups(keep: int = 3) -> List[Path]:
    archives = list_backups()
    if keep < 0:
        keep = 0
    removed = archives[:-keep] if keep else list(archives)
    keepers = archives[-keep:] if keep else []
    for path in removed:
        path.unlink(missing_ok=True)
    return removed
