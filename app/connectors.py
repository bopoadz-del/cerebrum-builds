"""Honest placeholder connectors. Offline platform — no network callbacks."""

STATUS = "not_implemented"

PLACEHOLDERS = (
    "pos_feed_stub",
    "supplier_portal_stub",
    "barcode_scanner_stub",
)


def connector_status(name: str) -> dict:
    return {"name": name, "status": STATUS, "implemented": False}
