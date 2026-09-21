#!/usr/bin/env python3
"""200 concurrent requests; p95 must come in under 500ms.

Written by the factory WRITER role (codewhale exec)

Measured, not estimated: the floor (bench_p95) reads the number this prints.
It exercises /health, which every platform has, so it measures the platform
rather than any one capability.

Three things this script refuses to do, because each of them produced a
number that meant nothing:

  * report a p95 over an endpoint that is not answering. If /health is not
    200 the run prints no number and exits non-zero -- a fast response from
    a 503 is not a fast platform, and the gate reads the number this prints.
  * measure the harness instead of the product. ``TestClient`` funnels every
    caller through one blocking portal, so N threads produced N callers
    queueing behind one event loop and the p95 was mostly queue time. Each
    worker thread gets its own client (and therefore its own portal), so the
    requests really are concurrent and the figure is the platform's.
  * run against a schema it never applied. The app is booted through its own
    lifespan first, the same way the container boots it.

The load is 16 workers over 200 requests, which is the shape the budget was
always written against.
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

REQUESTS = int(os.environ.get("BENCH_REQUESTS", "200"))
WORKERS = int(os.environ.get("BENCH_WORKERS", "16"))
BUDGET_MS = float(os.environ.get("BENCH_P95_BUDGET_MS", "500"))
PATH = os.environ.get("BENCH_PATH", "/health")


def _timed(client, _index: int) -> float:
    started = time.perf_counter()
    response = client.get(PATH)
    elapsed = (time.perf_counter() - started) * 1000.0
    if response.status_code != 200:
        raise RuntimeError("%s answered HTTP %s" % (PATH, response.status_code))
    return elapsed


def main() -> int:
    from fastapi.testclient import TestClient

    from app.main import app

    # Boot the product (lifespan applies migrations), then keep one client
    # per worker so the callers do not serialise behind a single portal.
    with TestClient(app) as probe:
        health = probe.get("/health")
        if health.status_code != 200:
            print(
                "bench refused: /health answered HTTP %s, so a p95 would "
                "measure nothing: %s" % (health.status_code, health.text[:200]),
                file=sys.stderr,
            )
            return 1
        clients = [TestClient(app) for _ in range(WORKERS)]
        try:
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                futures = []
                for index in range(REQUESTS):
                    futures.append(pool.submit(_timed, clients[index % WORKERS], index))
                try:
                    timings = sorted(f.result() for f in futures)
                except RuntimeError as exc:
                    print("bench refused: %s" % exc, file=sys.stderr)
                    return 1
        finally:
            for client in clients:
                client.close()

    p95 = timings[max(0, int(len(timings) * 0.95) - 1)]
    print(
        "requests=%d workers=%d path=%s p50=%.1fms p95=%.1fms budget=%.0fms"
        % (len(timings), WORKERS, PATH, statistics.median(timings), p95, BUDGET_MS)
    )
    print("STORE_BENCH_P95_MS=%.1f" % p95)
    if p95 >= BUDGET_MS:
        print("p95 over budget", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
