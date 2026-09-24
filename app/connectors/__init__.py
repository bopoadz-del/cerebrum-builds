"""Property-data connectors for CallOps (CHADi pilot).

Honest stubs remain for Twilio / CRM / WhatsApp. Live market sources:

* ``dxb_data`` — DXB Data MCP (official DLD area medians/yields)
* ``dld`` — dld-mcp HTTP data plane (DLD sales / Ejari rentals)
* ``apify_bayut`` — Apify Actor ``memo23/apify-bayut-scraper`` (Bayut for-sale)

Each live connector answers ``status: not_configured`` when its env is unset
and never fabricates market numbers. CI stays offline: tests mock all three.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.connectors import apify_bayut, dld, dxb_data

# Legacy honest stubs (Factory-named modules).
from app.connectors import (  # noqa: F401
    crm_salesforce_hubspot_zoho_for_call_outcome_and_broker_summary_shipping_as_a_marked_placeholder as crm_stub,
)
from app.connectors import (  # noqa: F401
    twilio_programmable_voice_voice_gateway_ships_stubbed_no_credentials_caller_number_provided as twilio_stub,
)
from app.connectors import whatsapp_webhook  # noqa: F401

MARKET_SOURCES = ("dxb_data", "dld", "apify_bayut")


def market_status() -> Dict[str, Any]:
    """Configuration snapshot for ``/v1/capabilities`` and operator runbooks."""
    items: List[Dict[str, Any]] = [
        dxb_data.status(),
        dld.status(),
        apify_bayut.status(),
    ]
    return {
        "sources": items,
        "configured": [s["source"] for s in items if s.get("status") == "configured"],
        "not_configured": [s["source"] for s in items if s.get("status") == "not_configured"],
        "cite_or_refuse": (
            "market connectors are explicit operator routes; they are not "
            "injected into project_knowledge_grounding — project sheet "
            "cite-or-refuse stays corpus-only"
        ),
    }


CONNECTORS = [
    {"id": "dxb_data", "module": "app.connectors.dxb_data", "env": [dxb_data.ENV_URL]},
    {"id": "dld", "module": "app.connectors.dld", "env": [dld.ENV_URL]},
    {"id": "apify_bayut", "module": "app.connectors.apify_bayut", "env": [apify_bayut.ENV_TOKEN]},
    {"id": "twilio_programmable_voice", "module": twilio_stub.__name__, "status": "stubbed"},
    {"id": "crm_destination", "module": crm_stub.__name__, "status": "placeholder"},
    {"id": "whatsapp_webhook", "module": whatsapp_webhook.__name__, "status": "not_implemented"},
]
