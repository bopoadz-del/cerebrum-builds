"""Backup and restore for the Bakery Chain Operations persistence root.

Written by the factory WRITER role (codewhale exec)

One database file, one backup directory, one drill: copy the live database with
sqlite's own backup API (WAL-safe — a filesystem ``cp`` of a WAL database
restores a database that is missing its last committed transactions), wipe, and
restore with the rows still there. ``STORAGE_PATH/platform.db`` is the only file
that carries domain state; the ``-wal``/``-shm`` sidecars are removed rather than
copied, because a restored main file paired with a stale WAL is corruption.

Retention is by name (``platform-<UTC stamp>.db``), newest kept, oldest pruned —
a backup directory that grows forever is a disk outage with a schedule.

Scope
-----
READS  ``STORAGE_PATH/platform.db``, ``BACKUP_DIR`` (filesystem).
WRITES ``BACKUP_DIR`` (backup files), ``STORAGE_PATH`` (restore).
NEVER  network, a second live database, ``vendor/**``.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app import store

#: How many backups a backup directory keeps by default.
DEFAULT_RETENTION = 7
BACKUP_PREFIX = "platform-"
BACKUP_SUFFIX = ".db"


def backup_root() -> Path:
    """Where backups live: ``BACKUP_DIR`` or ``STORAGE_PATH/backups``."""
    override = (os.environ.get("BACKUP_DIR") or "").strip()
    if override:
        return Path(override).expanduser()
    return store.db_path().parent / "backups"


def list_backups() -> List[Path]:
    """Every backup file, oldest name first (the stamp sorts lexically)."""
    root = backup_root()
    if not root.is_dir():
        return []
    return sorted(
        (path for path in root.glob(BACKUP_PREFIX + "*" + BACKUP_SUFFIX) if path.is_file()),
        key=lambda path: path.name,
    )


def create_backup() -> Path:
    """Snapshot the live database with sqlite's backup API and return the file."""
    source = store.db_path()
    if not source.is_file():
        raise FileNotFoundError(f"no database to back up at {source}")
    root = backup_root()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = root / f"{BACKUP_PREFIX}{stamp}{BACKUP_SUFFIX}"
    if target.exists():
        target = root / f"{BACKUP_PREFIX}{stamp}-{os.getpid()}{BACKUP_SUFFIX}"
    src = sqlite3.connect(str(source))
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()
    prune_backups()
    return target


def prune_backups(keep: int = DEFAULT_RETENTION) -> List[Path]:
    """Delete all but the newest *keep* backups; return what was removed."""
    backups = list_backups()
    limit = max(0, int(keep))
    doomed = backups[: len(backups) - limit] if limit else list(backups)
    removed: List[Path] = []
    for path in doomed:
        try:
            path.unlink()
        except OSError:
            continue
        removed.append(path)
    return removed


def wipe_database() -> Path:
    """Remove the live database and its WAL sidecars (a performed wipe)."""
    path = store.db_path()
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        try:
            candidate.unlink()
        except FileNotFoundError:
            continue
    return path


def restore_backup(archive: Optional[Path] = None) -> Path:
    """Restore *archive* (newest backup by default) over the live database."""
    source = Path(archive) if archive is not None else (list_backups()[-1] if list_backups() else None)
    if source is None or not source.is_file():
        raise FileNotFoundError("no backup to restore")
    target = store.db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    for sidecar in (Path(str(target) + "-wal"), Path(str(target) + "-shm")):
        try:
            sidecar.unlink()
        except FileNotFoundError:
            continue
    shutil.copyfile(source, target)
    return target
