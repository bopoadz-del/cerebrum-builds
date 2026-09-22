# CHADi / CallOps — property market connectors (pilot runbook)

Operator routes under `/v1/market/*` pull **official sold** and **asking**
context so brokers do not invent market numbers on the call. They are **not**
wired into `project_knowledge_grounding` (cite-or-refuse stays project-sheet
corpus only).

Auth: every route below requires `Authorization: Bearer $PLATFORM_TOKEN`
(fail-closed; unknown tenants still cannot read another tenant's rows on
capability surfaces — these market routes are read-through to external APIs
and do not persist).

## Enable on a pilot box

```sh
# Official DLD area medians / yields (DXB Data MCP JSON-RPC)
export DXB_DATA_MCP_URL=https://dxbdata.io/mcp

# DLD sales / Ejari — same data plane as:
#   uvx --with 'mcp<2' dld-mcp
# (must pin mcp<2 or FastMCP import fails)
export DLD_QUERY_URL=https://offerbrief.com/api

# Bayut for-sale harvest via Apify Actor memo23/apify-bayut-scraper
export APIFY_TOKEN=apify_api_...
```

Unset env → connector answers `status: not_configured` (no fabricated data).
CI never dials: `tests/conftest.py` blocks non-loopback sockets; tests mock
all three.

## Routes

| Method | Path | Body |
| --- | --- | --- |
| GET | `/v1/market/status` | — |
| POST | `/v1/market/dxb/snapshot` | `{"area":"Business Bay","property_type":"Flat"}` |
| POST | `/v1/market/dxb/yield` | `{"area":"JBR"}` → resolves to DLD `Marsa Dubai` |
| POST | `/v1/market/dxb/compare` | `{"areas":["Business Bay","Palm Jumeirah"]}` |
| POST | `/v1/market/dld/sales_stats` | `{"area":"Marina","property_type":"apartment"}` |
| POST | `/v1/market/apify/bayut_buy` | `{"startUrls":["https://www.bayut.com/for-sale/apartments/dubai/dubai-marina/"],"maxItems":25}` |

Apify harvests are capped (`maxItems` default 25, hard max 50). Do **not** use
`apify/web-fetch` for Bayut (Security check 503).

## Area naming

- DXB Data uses official DLD English labels. Broker shorthand **JBR** /
  **Dubai Marina** / **Marina** is aliased client-side to **Marsa Dubai** and
  the alias is reported on the response.
- dld-mcp / offerbrief fuzzy-matches Marina/JBR and often returns
  `area: Marsa Dubai` with `match_type: community_alias`.

## Honesty / remaining HotelOps gaps

Still stubbed or refused (unchanged):

- Twilio Programmable Voice until `TWILIO_*` + caller number
- CRM destination placeholder (no destination named)
- `CURRENCY` / `BROKER_COMMISSION_PERCENT` refused until set
- Google Drive stubbed without credentials
- Market numbers are **not** auto-grounded into cite-or-refuse
