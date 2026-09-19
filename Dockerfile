# Bakery Chain Operations & Delivery Platform — offline runtime image.
# Written by the factory WRITER role (codewhale exec)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STORAGE_PATH=/data \
    PORT=8000

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY vendor ./vendor
COPY kits ./kits
COPY blocks.lock.json ./
COPY docs ./docs
COPY README.md ./

RUN mkdir -p /data

# Fail-closed: the release gate refuses to build an image whose handlers,
# entities or health surface are incomplete.
RUN python3 scripts/release_gate.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["sh", "scripts/entrypoint.sh"]
