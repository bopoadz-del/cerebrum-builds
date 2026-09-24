"""Apify Bayut buy-side harvest connector.

Uses the Apify Actor API with ``APIFY_TOKEN``. Known-good Actor:
``memo23/apify-bayut-scraper`` with ``startUrls`` pointing at Bayut for-sale
search pages. Do **not** use ``apify/web-fetch`` for Bayut (Security check
503). Without ``APIFY_TOKEN`` the connector answers ``status: not_configured``
and never fabricates listing rows. Harvests are capped.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List
from urllib.parse import quote

from app.connectors._http import json_request
from app.security import InputRefused, clean_text

SOURCE_ID = "apify_bayut"
ENV_TOKEN = "APIFY_TOKEN"
ACTOR_ID = "memo23~apify-bayut-scraper"
ACTOR_SLUG = "memo23/apify-bayut-scraper"
API_BASE = "https://api.apify.com/v2"
DEFAULT_START_URL = "https://www.bayut.com/for-sale/property/dubai/"
DEFAULT_MAX_ITEMS = 25
HARD_MAX_ITEMS = 50
DEFAULT_WAIT_SECS = 120


def configured() -> bool:
    return bool((os.environ.get(ENV_TOKEN) or "").strip())


def token() -> str:
    return (os.environ.get(ENV_TOKEN) or "").strip()


def status() -> Dict[str, Any]:
    if not configured():
        return {
            "source": SOURCE_ID,
            "status": "not_configured",
            "env": ENV_TOKEN,
            "actor": ACTOR_SLUG,
            "error": (
                f"set {ENV_TOKEN} to enable Bayut for-sale harvest via "
                f"Actor {ACTOR_SLUG}; do not use apify/web-fetch for Bayut"
            ),
        }
    return {
        "source": SOURCE_ID,
        "status": "configured",
        "env": ENV_TOKEN,
        "actor": ACTOR_SLUG,
    }


def _not_configured() -> Dict[str, Any]:
    body = status()
    body["ok"] = False
    return body


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {token()}"}


def _cap_max_items(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_MAX_ITEMS
    return max(1, min(value, HARD_MAX_ITEMS))


def _normalize_start_urls(start_urls: Any) -> List[Dict[str, str]]:
    if start_urls is None or start_urls == "":
        urls = [DEFAULT_START_URL]
    elif isinstance(start_urls, str):
        urls = [start_urls]
    elif isinstance(start_urls, (list, tuple)):
        urls = list(start_urls)
    else:
        raise InputRefused("startUrls must be a string or list of Bayut for-sale URLs")
    out: List[Dict[str, str]] = []
    for item in urls:
        text = clean_text(item, field="startUrls", limit=500)
        if not text:
            continue
        if "bayut." not in text.casefold():
            raise InputRefused("startUrls must be Bayut URLs (bayut.com / bayut.sa / …)")
        # Prefer for-sale harvests; refuse accidental rent crawls unless operator is explicit.
        out.append({"url": text})
    if not out:
        raise InputRefused("startUrls is empty")
    if len(out) > 5:
        raise InputRefused("startUrls accepts at most 5 URLs")
    return out


def harvest_buy(
    *,
    start_urls: Any = None,
    max_items: Any = DEFAULT_MAX_ITEMS,
    wait_secs: Any = DEFAULT_WAIT_SECS,
    full_details: bool = False,
    _transport_run=None,
    _transport_items=None,
) -> Dict[str, Any]:
    """Run the Bayut Actor for for-sale listings and return capped dataset items.

    ``_transport_run`` / ``_transport_items`` are test hooks so the offline
    suite can mock the Actor API without opening a socket.
    """
    if not configured():
        return _not_configured()
    try:
        urls = _normalize_start_urls(start_urls)
        capped = _cap_max_items(max_items)
        try:
            wait_for = int(wait_secs)
        except (TypeError, ValueError):
            wait_for = DEFAULT_WAIT_SECS
        wait_for = max(0, min(wait_for, 300))
    except InputRefused as exc:
        return {"ok": False, "source": SOURCE_ID, "status": "error", "error": str(exc)}

    actor_input = {
        "startUrls": urls,
        "maxItems": capped,
        "fullDetails": bool(full_details),
    }

    if _transport_run is not None:
        run_body = _transport_run(actor_input)
        run_status = 201
    else:
        run_url = f"{API_BASE}/acts/{quote(ACTOR_ID)}/runs"
        query = {"waitForFinish": wait_for} if wait_for else None
        try:
            run_status, run_body, _ = json_request(
                run_url,
                method="POST",
                body=actor_input,
                headers=_auth_headers(),
                query=query,
                timeout=float(max(wait_for + 30, 60)),
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "source": SOURCE_ID,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}"[:300],
            }

    if run_status >= 400:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "http_status": run_status,
            "error": f"apify actor run HTTP {run_status}",
            "detail": run_body if isinstance(run_body, (dict, list, str)) else None,
        }

    run_data = run_body.get("data") if isinstance(run_body, dict) else None
    if not isinstance(run_data, dict):
        run_data = run_body if isinstance(run_body, dict) else {}
    run_id = run_data.get("id")
    dataset_id = run_data.get("defaultDatasetId")
    run_state = run_data.get("status")

    if run_state and str(run_state).upper() not in {"SUCCEEDED", "RUNNING", "READY"}:
        # Still return what we have; refuse to invent listings.
        if str(run_state).upper() in {"FAILED", "ABORTED", "TIMED-OUT"}:
            return {
                "ok": False,
                "source": SOURCE_ID,
                "status": "error",
                "error": f"apify actor run ended with status {run_state}",
                "run_id": run_id,
                "detail": run_data,
            }

    if _transport_items is not None:
        items = _transport_items(dataset_id or run_id)
        items_status = 200
    elif dataset_id:
        items_url = f"{API_BASE}/datasets/{quote(str(dataset_id))}/items"
        try:
            items_status, items, _ = json_request(
                items_url,
                method="GET",
                headers=_auth_headers(),
                query={"limit": capped, "clean": 1},
                timeout=60.0,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "source": SOURCE_ID,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}"[:300],
                "run_id": run_id,
                "dataset_id": dataset_id,
            }
    else:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "error": "apify actor run returned no defaultDatasetId",
            "run_id": run_id,
            "detail": run_data,
        }

    if items_status >= 400:
        return {
            "ok": False,
            "source": SOURCE_ID,
            "status": "error",
            "http_status": items_status,
            "error": f"apify dataset items HTTP {items_status}",
            "run_id": run_id,
            "dataset_id": dataset_id,
        }

    rows: List[Any]
    if isinstance(items, list):
        rows = items[:capped]
    else:
        rows = []

    return {
        "ok": True,
        "source": SOURCE_ID,
        "status": "ok",
        "actor": ACTOR_SLUG,
        "run_id": run_id,
        "dataset_id": dataset_id,
        "run_status": run_state,
        "capped_at": capped,
        "count": len(rows),
        "startUrls": [u["url"] for u in urls],
        "items": rows,
        "note": "asking prices from Bayut; not official DLD solds — cite source when pitching",
    }
