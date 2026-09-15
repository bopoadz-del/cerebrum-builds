"""JSON request logs without emoji. Correlation id is echoed."""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
LOGGER = logging.getLogger("platform.request")
_EMOJI = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U00002700-\U000027bf"
    "\U0001f000-\U0001f02f"
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    return _EMOJI.sub("", text or "")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "msg": strip_emoji(record.getMessage()),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        return json.dumps(payload, default=str)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        LOGGER.info("request %s %s", request.method, request.url.path, extra={"request_id": request_id})
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def install_request_logging(app) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = True
    app.add_middleware(RequestIdMiddleware)
