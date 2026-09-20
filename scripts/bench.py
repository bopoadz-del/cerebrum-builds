#!/usr/bin/env python3
"""Concurrency benchmark: 200 concurrent requests, p95 in milliseconds.

Written by the factory WRITER role (codewhale exec)

Runs against the in-process ASGI app (no server, no port: the factory owns
$PORT). Prints the measured number; it does not estimate one.

    python3 scripts/bench.py            # 200 requests, 20 threads
    BENCH_REQUESTS=500 BENCH_THREADS=32 python3 scripts/bench.py
"""

from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REQUESTS = int(os.environ.get("BENCH_REQUESTS") or 200)
THREADS = int(os.environ.get("BENCH_THREADS") or 20)
BUDGET_MS = float(os.environ.get("BENCH_BUDGET_MS") or 500.0)


def main() -> int:
    os.environ.setdefault("STORAGE_PATH", tempfile.mkdtemp(prefix="fleetops-bench-"))
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        client.get("/health")  # warm the schema and the block cache
        timings: list[float] = []

        def hit(_index: int) -> float:
            started = time.perf_counter()
            resp = client.get("/v1/jobs")
            elapsed = (time.perf_counter() - started) * 1000.0
            assert resp.status_code == 200, resp.status_code
            return elapsed

        with ThreadPoolExecutor(max_workers=THREADS) as pool:
            for elapsed in pool.map(hit, range(REQUESTS)):
                timings.append(elapsed)

    ordered = sorted(timings)
    p95 = ordered[min(int(len(ordered) * 0.95), len(ordered) - 1)]
    print(
        "requests=%d threads=%d p50=%.1fms p95=%.1fms max=%.1fms mean=%.1fms budget=%.0fms"
        % (
            len(ordered), THREADS,
            statistics.median(ordered), p95, ordered[-1],
            statistics.fmean(ordered), BUDGET_MS,
        )
    )
    print("VERDICT:", "PASS" if p95 <= BUDGET_MS else "FAIL")
    return 0 if p95 <= BUDGET_MS else 1


if __name__ == "__main__":
    sys.exit(main())
