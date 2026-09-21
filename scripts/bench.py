#!/usr/bin/env python3
"""200 concurrent requests; p95 must come in under 500ms.

Written by the factory. Measured, not estimated: the floor (bench_p95) reads
the number this prints. It exercises /health, which every platform has, so
it measures the platform rather than any one capability.
"""

from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

REQUESTS = int(os.environ.get("BENCH_REQUESTS", "200"))
BUDGET_MS = float(os.environ.get("BENCH_P95_BUDGET_MS", "500"))


def main() -> int:
    # Run from anywhere: this measures the platform, not the caller's cwd.
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    # A throwaway store unless the caller named one: the bench measures the
    # platform, and a benchmark that also migrates the checkout's data/ leaves
    # build artefacts behind (and can fight a running dev database).
    default_storage = tempfile.mkdtemp(prefix="callops-bench-")
    storage = os.environ.setdefault("STORAGE_PATH", default_storage)
    os.makedirs(storage, exist_ok=True)
    from app.migrations import upgrade_head

    upgrade_head()

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    def once(_):
        started = time.perf_counter()
        client.get("/health")
        return (time.perf_counter() - started) * 1000.0

    with ThreadPoolExecutor(max_workers=16) as pool:
        timings = sorted(pool.map(once, range(REQUESTS)))

    p95 = timings[max(0, int(len(timings) * 0.95) - 1)]
    print(
        "requests=%d p50=%.1fms p95=%.1fms budget=%.0fms"
        % (len(timings), statistics.median(timings), p95, BUDGET_MS)
    )
    print("STORE_BENCH_P95_MS=%.1f" % p95)
    if p95 >= BUDGET_MS:
        print("p95 over budget", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
