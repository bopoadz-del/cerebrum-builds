#!/bin/sh
# Rollback: drop the schema to base and stop. Data files are left in place.
# Written by the factory WRITER role (codewhale exec)
set -e
python - <<'PY'
from app.migrations import downgrade_base
downgrade_base()
print("schema rolled back to base")
PY
