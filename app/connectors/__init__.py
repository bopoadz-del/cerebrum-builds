"""Connector register: every external integration this platform does NOT have.

Written by the factory WRITER role (codewhale exec)

The platform is offline. Rather than shipping half a connector, this module
declares the honest state of each integration so a reader never has to guess
whether "the ERP link" exists. Nothing here is callable.

Scope
-----
READS  nothing.
WRITES nothing.
NEVER  network, credentials, `vendor/**`.
"""

from __future__ import annotations

from typing import Any, Dict, List

PLACEHOLDERS: List[Dict[str, Any]] = [
    {"id": "erp_sync", "status": "not_implemented", "note": "no ERP endpoint is configured; batch records stay local"},
    {"id": "lims_lab_results", "status": "not_implemented", "note": "lab results are entered through the API"},
    {"id": "opcua_plc", "status": "not_implemented", "note": "no OPC-UA client ships offline"},
    {"id": "email_smtp", "status": "not_implemented", "note": "notifications use the MCP channel and a local outbox"},
]


def register() -> Dict[str, Any]:
    return {"implemented": [], "placeholders": PLACEHOLDERS}
