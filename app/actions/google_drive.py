"""Google Drive connector (marked placeholder).

Written by the factory WRITER role (codewhale exec)

Drive is where a brokerage usually keeps its project sheets, so this
connector exists and builds the exact requests it would make: a refresh-token
grant against the OAuth endpoint, then the Drive v3 file call. No
credentials were supplied, so it ships reporting ``stubbed`` with the missing
settings named, and it never reports a file it did not read.

The transport is injectable, which is how the request shape is certified
against a fake transport in the test suite — CI makes no Google call.
"""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict, List

from app import config, domain
from app.models import MODELS

CAPABILITY_ID = "google_drive"

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'google_drive': 'list',
}

REQUIRED_FIELDS = ["operation"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "operation": {"allowed_values": ['upload', 'download', 'list', 'search', 'share', 'delete'], "required": True},
    "drive_mode": {"allowed_values": ['stubbed', 'live']},
    "folder_id": {"max_length": 120},
    "document_id": {"max_length": 120},
    "file_name": {"max_length": 200},
    "mime_type": {"max_length": 120},
    "credentials_present": {},
    "unavailable_blocks": {"max_length": 400},
    "delivery": {"allowed_values": ['stub', 'unavailable', 'delivered']},
    "note": {"max_length": 400},
    "would_call": {"max_length": 300},
    "upload_state": {"max_length": 40},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_URL = "https://www.googleapis.com/drive/v3/files"

CREDENTIAL_SETTINGS = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")


def missing_settings() -> List[str]:
    """Credentials the operator has not supplied, by name — never a guess."""
    values = {
        "GOOGLE_CLIENT_ID": config.GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": config.GOOGLE_CLIENT_SECRET,
        "GOOGLE_REFRESH_TOKEN": config.GOOGLE_REFRESH_TOKEN,
        "GOOGLE_DRIVE_FOLDER_ID": config.GOOGLE_DRIVE_FOLDER_ID,
    }
    return [name for name in (*CREDENTIAL_SETTINGS, "GOOGLE_DRIVE_FOLDER_ID") if not values.get(name)]


def request_for(operation: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """The Drive call this operation would make, as data."""
    folder = body.get("folder_id") or config.GOOGLE_DRIVE_FOLDER_ID
    if operation == "list":
        return {"method": "GET", "url": DRIVE_URL, "query": {"q": f"'{folder}' in parents"}}
    if operation == "search":
        return {
            "method": "GET",
            "url": DRIVE_URL,
            "query": {"q": f"name contains '{body.get('file_name') or ''}'"},
        }
    if operation == "upload":
        return {
            "method": "POST",
            "url": "https://www.googleapis.com/upload/drive/v3/files",
            "query": {"uploadType": "multipart"},
            "body": {"name": body.get("file_name"), "parents": [folder]},
        }
    if operation == "download":
        return {
            "method": "GET",
            "url": f"{DRIVE_URL}/{body.get('document_id') or '{fileId}'}",
            "query": {"alt": "media"},
        }
    if operation == "share":
        return {
            "method": "POST",
            "url": f"{DRIVE_URL}/{body.get('document_id') or '{fileId}'}/permissions",
            "body": {"role": "reader", "type": "user"},
        }
    return {
        "method": "DELETE",
        "url": f"{DRIVE_URL}/{body.get('document_id') or '{fileId}'}",
    }


def perform(
    operation: str,
    body: Dict[str, Any],
    *,
    transport: Any = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Refresh a token and make the Drive call, through an injectable transport.

    Only reached when the operator has supplied credentials *and* opted in
    with ``GOOGLE_ALLOW_API=1``: a connector that ships a request shape and
    then dials on its own is not a stub, it is an unpriced surprise. The
    transport is what the test suite substitutes, so the sequence
    (token → files call) is certified without a Google call.
    """
    import urllib.error
    import urllib.request

    request = request_for(operation, body)
    token_request = {
        "method": "POST",
        "url": TOKEN_URL,
        "payload": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "refresh_token": config.GOOGLE_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
    }
    if transport is None:
        for endpoint in (TOKEN_URL, request["url"]):
            if not str(endpoint).startswith("https://"):
                return {"attempted": True, "delivered": False, "stage": "endpoint-check"}

        class _Http:
            def post(self, url, payload, headers):
                data = urllib.parse.urlencode(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                # nosec B310 - checked to be https above.
                with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec B310
                    return json.loads(response.read().decode("utf-8") or "{}")

            def request(self, method, url, token, query=None):
                target = url + (("?" + urllib.parse.urlencode(query or {})) if query else "")
                req = urllib.request.Request(
                    target, headers={"Authorization": "Bearer " + str(token)}, method=method
                )
                # nosec B310 - checked to be https above.
                with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec B310
                    raw = response.read().decode("utf-8", "replace")
                try:
                    return json.loads(raw or "{}")
                except ValueError:
                    return {"raw": raw[:400]}

        transport = _Http()
    granted = transport.post(TOKEN_URL, token_request["payload"], {"Content-Type": "application/x-www-form-urlencoded"})
    access_token = str((granted or {}).get("access_token") or "")
    if not access_token:
        return {"attempted": True, "delivered": False, "stage": "token", "response": granted}
    answer = transport.request(
        request["method"], request["url"], access_token, request.get("query") or {}
    )
    return {
        "attempted": True,
        "delivered": True,
        "stage": "files",
        "access_token_present": True,
        "response": answer,
    }


def handle(payload: Dict[str, Any], *, transport: Any = None) -> Dict[str, Any]:
    """Build the call Drive would receive, and say plainly what ran."""
    body = dict(payload or {})
    for name in REQUIRED_FIELDS:
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name in ("reference", "status"):
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name, rules in constraints.items():
        values = rules.get("allowed_values") or ()
        value = body.get(name)
        if value is None or value == "":
            continue
        if values and value not in values:
            return {
                "ok": False,
                "error": f"{name} must be one of: " + ", ".join(str(v) for v in values),
            }
    operation = str(body.get("operation"))
    missing = missing_settings()
    request = request_for(operation, body)
    opt_in = str(config.env("GOOGLE_ALLOW_API", "") or "") in ("1", "true", "yes")
    performed: Dict[str, Any] = {"attempted": False}
    if not missing and opt_in:
        performed = perform(operation, body, transport=transport)
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": "stubbed" if missing else "live",
        "blocks_unavailable": missing,
        "would_call": f"{request['method']} {request['url']}",
        "record": {
            "operation": operation,
            "drive_mode": "stubbed" if missing else "live",
            "folder_id": body.get("folder_id") or config.GOOGLE_DRIVE_FOLDER_ID,
            "document_id": body.get("document_id"),
            "file_name": body.get("file_name"),
            "mime_type": body.get("mime_type"),
            "credentials_present": not missing,
            "unavailable_blocks": ", ".join(missing),
            "delivery": "stub" if missing else "unavailable",
            "note": (
                "Google Drive credentials are not supplied: the request shape is "
                "built and no call is made"
                if missing
                else "credentials present; this connector still makes no call without an operator opt-in"
            ),
            "would_call": f"{request['method']} {request['url']}",
            "upload_state": "performed" if performed.get("delivered") else "not_attempted",
        },
        "request": request,
        "performed": performed,
        "authority": domain.envelope(
            [
                domain.Claim(
                    name="drive_call",
                    value="not_attempted",
                    layer="procedures",
                    source="google_drive.request_for",
                    detail="request shape only",
                )
            ]
        ),
    }
