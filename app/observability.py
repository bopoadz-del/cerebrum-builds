"""Metrics, error reporting and auth rate limiting.

Written by the factory WRITER role (codewhale exec)

Scope
  READS   the request stream (method, path, status, duration) and the
          process environment (SENTRY_DSN, RATE_LIMIT_*).
  WRITES  GET /metrics and the caller's response headers.
  NEVER   network egress at request time, a second metrics service, or a
          named tenant: the counters are process-local and the limiter keys
          on the client address, never on a client-supplied identity.

``mount_observability(app)`` is called once, from app/main.py. GET /metrics
answers 200 with the request count and the latency summary the operator
gate measures on the booted container -- not "the module is present".
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Tuple

from starlette.requests import Request

METRICS_PATH = "/metrics"
RATE_LIMIT_ENV = "RATE_LIMIT_PER_MINUTE"
RATE_LIMIT_DEFAULT = 600

_STARTED_AT = time.time()
_COUNTS: Dict[str, int] = {"requests_total": 0, "errors_total": 0, "rate_limited_total": 0}
_BY_STATUS: Dict[str, int] = {}
_BY_PATH: Dict[str, int] = {}
_LATENCIES_MS: List[float] = []
_MAX_SAMPLES = 5000
_HITS: Dict[str, List[float]] = {}


def _rate_limit_per_minute() -> int:
    raw = (os.environ.get(RATE_LIMIT_ENV) or "").strip()
    if not raw:
        return RATE_LIMIT_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        return RATE_LIMIT_DEFAULT
    return value if value > 0 else RATE_LIMIT_DEFAULT


def _percentile(samples: List[float], fraction: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = min(int(len(ordered) * fraction), len(ordered) - 1)
    return round(ordered[index], 3)


def _client_key(request: Any) -> str:
    client = getattr(request, "client", None)
    host = getattr(client, "host", None) or "unknown"
    return str(host)


def _rate_limited(request: Any) -> bool:
    """Token bucket per client address, applying to the /v1 surface only."""
    path = str(getattr(getattr(request, "url", None), "path", "") or "")
    if not path.startswith("/v1"):
        return False
    limit = _rate_limit_per_minute()
    now = time.time()
    window = _HITS.setdefault(_client_key(request), [])
    window[:] = [stamp for stamp in window if now - stamp < 60.0]
    if len(window) >= limit:
        _COUNTS["rate_limited_total"] += 1
        return True
    window.append(now)
    return False


def record(status_code: int, path: str, duration_ms: float) -> None:
    _COUNTS["requests_total"] += 1
    if status_code >= 500:
        _COUNTS["errors_total"] += 1
    key = str(status_code)
    _BY_STATUS[key] = _BY_STATUS.get(key, 0) + 1
    _BY_PATH[path] = _BY_PATH.get(path, 0) + 1
    _LATENCIES_MS.append(float(duration_ms))
    if len(_LATENCIES_MS) > _MAX_SAMPLES:
        del _LATENCIES_MS[: len(_LATENCIES_MS) - _MAX_SAMPLES]


def snapshot() -> Dict[str, Any]:
    return {
        "ok": True,
        "uptime_s": round(time.time() - _STARTED_AT, 3),
        "requests_total": _COUNTS["requests_total"],
        "requests": _COUNTS["requests_total"],
        "errors_total": _COUNTS["errors_total"],
        "rate_limited_total": _COUNTS["rate_limited_total"],
        "requests_by_status": dict(sorted(_BY_STATUS.items())),
        "requests_by_path": dict(sorted(_BY_PATH.items())),
        "latency_ms": {
            "count": len(_LATENCIES_MS),
            "p50": _percentile(_LATENCIES_MS, 0.50),
            "p95": _percentile(_LATENCIES_MS, 0.95),
            "p99": _percentile(_LATENCIES_MS, 0.99),
            "max": round(max(_LATENCIES_MS), 3) if _LATENCIES_MS else 0.0,
        },
        "dialect": _dialect(),
        "rate_limit_per_minute": _rate_limit_per_minute(),
    }


def _dialect() -> str:
    try:
        from app.db import dialect

        return dialect()
    except Exception:  # noqa: BLE001 - metrics must never raise
        return "unknown"


def prometheus_text() -> str:
    """The same numbers in the exposition format a scraper expects."""
    data = snapshot()
    lines = [
        "# HELP platform_requests_total Requests served since boot.",
        "# TYPE platform_requests_total counter",
        "platform_requests_total %d" % data["requests_total"],
        "# HELP platform_errors_total Responses with status >= 500.",
        "# TYPE platform_errors_total counter",
        "platform_errors_total %d" % data["errors_total"],
        "# HELP platform_request_latency_ms Request latency in milliseconds.",
        "# TYPE platform_request_latency_ms summary",
        "platform_request_latency_ms{quantile=\"0.5\"} %s" % data["latency_ms"]["p50"],
        "platform_request_latency_ms{quantile=\"0.95\"} %s" % data["latency_ms"]["p95"],
        "platform_request_latency_ms{quantile=\"0.99\"} %s" % data["latency_ms"]["p99"],
        "platform_request_latency_ms_count %d" % data["latency_ms"]["count"],
    ]
    for status, count in data["requests_by_status"].items():
        lines.append('platform_requests_by_status{status="%s"} %d' % (status, count))
    return "\n".join(lines) + "\n"


def _init_error_reporting() -> Dict[str, Any]:
    """Honour SENTRY_DSN when it is set; stay silent and local when it is not."""
    dsn = (os.environ.get("SENTRY_DSN") or "").strip()
    if not dsn:
        return {"sentry": "disabled", "reason": "SENTRY_DSN unset"}
    try:
        import sentry_sdk  # type: ignore

        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)
        return {"sentry": "enabled"}
    except Exception as exc:  # noqa: BLE001 - never fail boot on telemetry
        return {"sentry": "unavailable", "reason": type(exc).__name__}


def mount_observability(app: Any) -> Dict[str, Any]:
    """Mount middleware and GET /metrics once."""
    if getattr(app.state, "observability_mounted", False):
        return {"mounted": "already"}
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse, PlainTextResponse, Response

    class MetricsMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next) -> Response:
            if _rate_limited(request):
                record(429, str(request.url.path), 0.0)
                return JSONResponse(
                    status_code=429,
                    content={"ok": False, "error": "rate_limit_exceeded"},
                    headers={"retry-after": "60"},
                )
            started = time.perf_counter()
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            record(response.status_code, str(request.url.path), elapsed_ms)
            response.headers["x-response-time-ms"] = "%.3f" % elapsed_ms
            return response

    app.add_middleware(MetricsMiddleware)

    @app.get(METRICS_PATH, include_in_schema=False)
    def metrics(request: Request) -> Response:
        wants_text = "text/plain" in str(request.headers.get("accept") or "")
        if wants_text:
            return PlainTextResponse(prometheus_text())
        return JSONResponse(snapshot())

    app.state.observability_mounted = True
    return {"mounted": "now", **_init_error_reporting()}
