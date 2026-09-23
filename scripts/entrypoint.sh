#!/bin/sh
# Apply versioned migrations against the persistent disk, then serve.
# Failure here refuses boot (fail-closed). Do not start uvicorn on a
# schema that is behind head.
#
# The image ENTRYPOINT and the Procfile ("web: sh scripts/entrypoint.sh")
# both run this file, so it resolves the repository root from its own path
# instead of assuming the image's /app: a checkout, a Heroku-style slug and a
# container all boot the same way.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

# STORAGE_PATH is the platform's one persistence root and /health reports 503
# while it is missing. On the SQLite path alembic creates it; with
# DATABASE_URL pointing at the operator's Postgres nothing else does, so make
# it here — otherwise a correctly migrated Postgres deploy never goes green.
STORAGE="${STORAGE_PATH:-./data}"
mkdir -p "$STORAGE"

python -m alembic upgrade head
python -c "import json, os; print(json.dumps({'event': 'entrypoint.start', 'revision': os.getenv('APP_REVISION', ''), 'storage': os.getenv('STORAGE_PATH', ''), 'port': os.getenv('PORT', '8000')}))"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
