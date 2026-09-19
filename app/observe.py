"""Structured request observation for the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

One JSON line per answered request on the ``platform.request`` logger, each
carrying the correlation id the caller sent (``X-Request-Id``) or the one the
platform minted. The formatter is deliberately dumb: one JSON object per line,
no colour, no emoji — a log line an operator can grep and a machine can parse.
Emoji is stripped rather than escaped: a block that prints a celebration emoji
mid-pipeline must not corrupt the log stream.

Scope
-----
READS  the request headers/status.
WRITES stdout/stderr (the log stream).
NEVER  network, a log file, ``vendor/**``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

REQUEST_ID_HEADER = "X-Request-Id"
LOGGER_NAME = "platform.request"

#: Emoji / pictograph ranges that must never reach the log stream.
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0000FE0F"
    "\U0001F900-\U0001F9FF"
    "\U00002190-\U000021FF"
    "\U00002700-\U000027BF"
    "]"
)


def strip_emoji(text: Any) -> str:
    """Return *text* without emoji or pictographs.

    Whitespace is left exactly as it was: a log line's trailing space is part
    of the message a reader searches for, and trimming it would make ``ready 🎉``
    and ``ready`` indistinguishable in the record.
    """
    return _EMOJI_RE.sub("", str(text if text is not None else ""))


class JsonFormatter(logging.Formatter):
    """Render a log record as one JSON object, emoji-free."""

    EXTRA_FIELDS = ("request_id", "method", "path", "status_code", "capability_id")

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": str(record.levelname),
            "logger": str(record.name),
            "msg": strip_emoji(record.getMessage()),
        }
        for field in self.EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = strip_emoji(value) if isinstance(value, str) else value
        if record.exc_info:
            payload["exc"] = strip_emoji(self.formatException(record.exc_info))
        return json.dumps(payload, sort_keys=True)


def request_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Attach the JSON formatter once (idempotent across imports/reloads)."""
    logger = request_logger()
    logger.setLevel(level)
    logger.propagate = True
    if not any(getattr(handler, "_bakery_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler._bakery_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return logger


def log_request(request_id: str, method: str, path: str, status_code: int) -> None:
    """Record one answered request. Never raises into the request path."""
    try:
        request_logger().info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
            },
        )
    except Exception:  # noqa: BLE001 - observation must not break the request
        pass
