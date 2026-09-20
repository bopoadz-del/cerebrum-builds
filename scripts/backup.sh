#!/bin/sh
# Back up the live database onto the backup volume.
#
# Written by the factory WRITER role (codewhale exec)
#
# Uses SQLite's online backup API through app.backup, so a live writer cannot
# produce a torn snapshot. The output restores into an empty database with the
# rows intact -- tests/test_backup_restore.py drills exactly that.
#
#   sh scripts/backup.sh              # $STORAGE_PATH/platform.db -> $BACKUP_DIR
#   STORAGE_PATH=/app/data sh scripts/backup.sh
#
# stdout is the archive path, one line, last: that is what a cron wrapper or
# a restore drill consumes. The structured event goes to stderr so a human
# reading the journal still sees it without breaking `archive=$(backup.sh)`.
#
# Same-disk BACKUP_DIR protects against logical loss, not disk loss: set
# BACKUP_DIR onto another volume if disk loss is in scope.
set -eu
cd "$(dirname "$0")/.."
python3 - "$@" <<'PY'
import json
import sys

from app.backup import backup_root, create_backup, list_backups

archive = create_backup()
print(json.dumps({
    "event": "backup.complete",
    "archive": str(archive),
    "backup_dir": str(backup_root()),
    "retained": len(list_backups()),
}), file=sys.stderr)
print(archive)
sys.exit(0)
PY
