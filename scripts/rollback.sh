#!/bin/sh
# Roll the running identity back to a prior revision.
# Does not wipe STORAGE_PATH/platform.db — persisted rows stay.
# Render equivalent: Dashboard rollback to the previous deploy
# (same disk). Losing that disk is still a SPOF; this script
# cannot invent a replica.
#
# What a rollback actually changes: app/revision.py reports APP_REVISION and
# APP_MARK from the environment, so the revision a running process claims is
# set when it restarts. This script writes the on-disk record
# (STORAGE_PATH/deploy_revision) and prints the environment the restart needs;
# doing only the file would leave the platform reporting the old revision.
# The schema is not downgraded: boot applies alembic upgrade head.
set -eu
TARGET="${1:?usage: rollback.sh <revision> [mark]}"
MARK="${2:-baseline}"
STORAGE="${STORAGE_PATH:?STORAGE_PATH required}"
mkdir -p "$STORAGE"
printf '%s\n' "$TARGET" > "$STORAGE/deploy_revision"
printf '%s\n' "{\"event\":\"rollback.performed\",\"revision\":\"$TARGET\",\"storage\":\"$STORAGE\"}"
printf 'rollback.sh: restart the process with APP_REVISION=%s APP_MARK=%s (Render: roll back the deploy; same disk, same schema at head)\n' "$TARGET" "$MARK" >&2
