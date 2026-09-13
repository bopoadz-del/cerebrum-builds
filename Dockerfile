FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    STORAGE_PATH=/app/data \
    PORT=8000

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
COPY openapi.json /app/openapi.json
COPY openapi.json /app/docs/openapi.json
RUN mkdir -p /app/data

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
