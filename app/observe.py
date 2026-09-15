"""JSON request logs with correlation id. No emoji in rendered output."""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"

_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U00002700-\U000027bf"
    "\U0001f000-\U0001f02f"
    "\U0001f0a0-\U0001f0ff"
    "\U00002600-\U000026ff"
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", str(text or ""))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "logger": record.name,
            "level": record.levelname,
            "msg": strip_emoji(record.getMessage()),
            "request_id": getattr(record, "request_id", None),
        }
        return json.dumps(payload, default=str)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        logger = logging.getLogger("platform.request")
        logger.info(
            "%s %s",
            request.method,
            request.url.path,
            extra={"request_id": request_id},
        )
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def configure_request_logging() -> None:
    logger = logging.getLogger("platform.request")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
