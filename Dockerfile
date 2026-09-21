# Standalone image. Blocks are vendored into the repository at build
# time. Network posture: P1 — no outbound at runtime.
#
# Two stages, because the repository carries two UI artifacts and the image
# must not ship one of them dead:
#
#   * ``app/static/index.html`` is the console the platform serves at ``/``.
#     It is dependency-free, needs no bundler, and works on an air-gapped
#     host; the pilot harness drives it end to end.
#   * ``frontend/`` is the same console in React components (the declared UI
#     modules live there). The ``console`` stage builds and type-checks it
#     with npm, so the image proves the source compiles and ships the bundle
#     at ``/app/frontend-dist``. It deliberately does NOT overwrite
#     ``app/static``: one UI is served, and it is the one the tests exercise.
FROM node:18-slim AS console
WORKDIR /ui
COPY frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/src ./src
RUN npm install --no-audit --no-fund \
 && npx tsc --noEmit \
 && npx vite build --outDir dist --emptyOutDir

# Base image pin: Docker Hub library/python:3.12-slim (2026-08-23).
FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .
# The built React console, from the stage above.
COPY --from=console /ui/dist /app/frontend-dist
ENV PYTHONPATH=/app
# Persistence is a sqlite file on the mounted disk (F23).
ENV STORAGE_PATH=/app/data
RUN mkdir -p /app/data

# F19: a red suite must not produce a deployable image.
RUN python3 scripts/release_gate.py

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# S10: migrate against the persistent disk, then serve. Failure refuses boot.
# scripts/entrypoint.sh: alembic upgrade head && uvicorn app.main:app
ENTRYPOINT ["sh", "/app/scripts/entrypoint.sh"]
