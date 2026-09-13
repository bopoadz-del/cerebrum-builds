# Tiny Smoke Retail Inventory Tracker

Cerebrum-builds session for **Tiny Smoke Retail Inventory Tracker** — a lightweight inventory tracking application for tiny smoke retail shops. Owners manage products, monitor stock levels, and receive low-stock alerts. Manufactured from vendored Store blocks (`database`, `storage`, `validation`, `audit`, `notification`, `event_bus`, `queue`, `team`, `dashboard`, `analytics`, `workflow`).

Private Factory CLI-pivot scratch store. One branch per session. Store gate = GHA docker + `scripts/acceptance.py` (not Render).

## Roles

- operator
- admin

Mutating routes require `OPERATOR_TOKEN` / `ADMIN_TOKEN`. CORS uses `CORS_ALLOWLIST` only (`*` is refused).
