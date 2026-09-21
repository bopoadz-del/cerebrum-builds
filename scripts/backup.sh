#!/usr/bin/env bash
# Take a backup of whatever this platform stores on.
#
#   DATABASE_URL set   -> pg_dump
#   DATABASE_URL unset -> SQLite online backup of STORAGE_PATH/platform.db
#
# The SQLite leg prefers the sqlite3 CLI and falls back to the Python stdlib
# (the same .backup() API app/backup.py uses). The image ships python, not the
# sqlite3 CLI, so a backup path that only existed via the CLI would be a
# backup path that does not exist in production. The Postgres leg cannot be
# stood in for: a missing pg_dump is named and refused rather than written out
# as a file that is not a dump.
#
# Written by the factory. A backup nobody has restored is a file, not a
# backup: tests/test_backup_restore.py restores what this produces.
set -euo pipefail

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

py() {
  if command -v python3 >/dev/null 2>&1; then
    python3 "$@"
  elif command -v python >/dev/null 2>&1; then
    python "$@"
  else
    echo "backup.sh: no python3 on PATH for the stdlib fallback" >&2
    exit 2
  fi
}

if [ -n "${DATABASE_URL:-}" ]; then
  OUT="${1:-${BACKUP_DIR:-./backups}}"
  mkdir -p "$OUT"
  DEST="$OUT/platform-$STAMP.sql"
  if ! command -v pg_dump >/dev/null 2>&1; then
    echo "backup.sh: pg_dump is not installed on this host and is not in the app image." >&2
    echo "Run the backup where the Postgres client lives, or use the managed database's own snapshots." >&2
    exit 2
  fi
  pg_dump "$DATABASE_URL" > "$DEST"
else
  SRC="${STORAGE_PATH:-./data}/platform.db"
  OUT="${1:-${BACKUP_DIR:-${STORAGE_PATH:-./data}/backups}}"
  mkdir -p "$OUT"
  DEST="$OUT/platform-$STAMP.db"
  if [ ! -f "$SRC" ]; then
    echo "no database at $SRC" >&2
    exit 1
  fi
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$SRC" ".backup '$DEST'"
  else
    py - "$SRC" "$DEST" <<'PY'
import sqlite3
import sys

src, dest = sys.argv[1], sys.argv[2]
source = sqlite3.connect(src)
target = sqlite3.connect(dest)
try:
    # The online backup API, not a file copy: a live writer cannot produce a
    # torn snapshot.
    source.backup(target)
finally:
    target.close()
    source.close()
PY
  fi
  if [ ! -f "$DEST" ]; then
    echo "backup.sh: $DEST was not written" >&2
    exit 1
  fi
fi

echo "$DEST"
