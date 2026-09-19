#!/bin/sh
# Container entrypoint: migrate to head, then serve.
# Written by the factory WRITER role (codewhale exec)
set -e

STORAGE_PATH="${STORAGE_PATH:-/data}"
export STORAGE_PATH
mkdir -p "$STORAGE_PATH"

python - <<'PY'
import os
from app.migrations import upgrade_head
upgrade_head()
print("storage:", os.environ.get("STORAGE_PATH"))
PY

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
