"""Shared outbound HTTP for property-data connectors.

Uses stdlib ``urllib`` only — no extra runtime dependency. Cloudflare (and
similar edges) ban the default Python user-agent; connectors send an explicit
CallOps UA. CI still cannot dial: ``tests/conftest.py`` blocks non-loopback
sockets, so every live path is mocked in the offline suite.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Mapping, MutableMapping, Optional, Tuple

USER_AGENT = (
    "Mozilla/5.0 (compatible; CallOps/1.0; "
    "+https://github.com/bopoadz-del/cerebrum-builds)"
)


def json_request(
    url: str,
    *,
    method: str = "GET",
    body: Any = None,
    headers: Optional[Mapping[str, str]] = None,
    timeout: float = 30.0,
    query: Optional[Mapping[str, Any]] = None,
) -> Tuple[int, Any, Dict[str, str]]:
    """HTTP JSON round-trip. Returns ``(status, parsed_body, response_headers)``.

    ``parsed_body`` is a dict/list when the response is JSON, otherwise the
    decoded text. Raises ``urllib.error.URLError`` / ``HTTPError`` on transport
    failure; callers map those onto connector refusals.
    """
    target = url
    if query:
        qs = urllib.parse.urlencode(
            {k: v for k, v in query.items() if v is not None and v != ""},
            doseq=True,
        )
        target = f"{url}?{qs}" if qs else url

    hdrs: MutableMapping[str, str] = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if headers:
        hdrs.update({str(k): str(v) for k, v in headers.items()})

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    request = urllib.request.Request(target, data=data, headers=dict(hdrs), method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(getattr(response, "status", 200) or 200)
            resp_headers = {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        status = int(exc.code)
        resp_headers = {k.lower(): v for k, v in (exc.headers or {}).items()}
        parsed = _parse_body(raw, resp_headers)
        return status, parsed, resp_headers

    return status, _parse_body(raw, resp_headers), resp_headers


def _parse_body(raw: bytes, headers: Mapping[str, str]) -> Any:
    text = (raw or b"").decode("utf-8", errors="replace")
    if not text.strip():
        return None
    ctype = (headers.get("content-type") or "").lower()
    if "json" in ctype or text.lstrip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except ValueError:
            return text
    return text
