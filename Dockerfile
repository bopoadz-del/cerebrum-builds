# CallOps. Two stages, because the repository ships two UI artefacts and the
# image must not ship one of them dead:
#
#   * app/static/index.html is the console served at /. It is dependency-free,
#     needs no bundler, and is what the tests and the pilot drive.
#   * frontend/ is the same console in React components (the declared UI
#     modules live there). The console stage installs, type-checks and bundles
#     it, so the source can never rot; the bundle is served at /console
#     (app/main.py mounts ROOT/frontend-dist when it exists).
#
# Blocks are composed in process (app/dispatch.py): the runtime makes no
# outbound call except the operator's webhook, which is guarded.

FROM node:18-slim AS console
WORKDIR /ui
# The lockfile is copied and `npm ci` is used: the bundle a deploy serves is
# the one this repository pins, not whatever the registry resolved that
# morning. A lockfile out of step with package.json fails the build here
# rather than drifting silently into the image.
COPY frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/src ./src
RUN npm ci --no-audit --no-fund \
 && npx tsc --noEmit \
 && npx vite build --outDir dist --emptyOutDir

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt requirements-dev.txt ./
# requirements-dev.txt is installed on purpose: the release gate below runs
# the code-phase suite inside the image, so a red suite cannot be published.
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
COPY . .
COPY --from=console /ui/dist /app/frontend-dist
ENV PYTHONPATH=/app
ENV STORAGE_PATH=/app/data
RUN mkdir -p /app/data

# A red suite must not produce a deployable image. The gate migrates a
# throwaway root and probes /health, so a broken packaging contract fails the
# build rather than the deploy. Its own build artefacts are removed
# afterwards: the image ships no database, and the runtime root is created
# (and migrated) on boot.
RUN python3 scripts/release_gate.py \
 && rm -rf /app/data \
 && mkdir -p /app/data

EXPOSE 8000

# The probe follows PORT: ENTRYPOINT binds "${PORT:-8000}" and every container
# host (Render included) assigns PORT, so a healthcheck pinned to 8000 would
# report a healthy container unhealthy and keep it out of rotation. /health is
# fail-closed — it answers 503 until STORAGE_PATH is writable, platform.db
# opens and alembic is at head — so this cannot green an unmigrated container.
# --start-period covers the migrations the entrypoint applies before uvicorn
# binds.
HEALTHCHECK --interval=10s --timeout=3s --start-period=40s --retries=3 \
  CMD python3 -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health', timeout=2)"

# scripts/entrypoint.sh: alembic upgrade head, then uvicorn. Failure refuses boot.
ENTRYPOINT ["sh", "/app/scripts/entrypoint.sh"]
