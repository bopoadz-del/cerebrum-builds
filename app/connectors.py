"""Honest placeholder connectors. Offline platform — no network callbacks."""

STATUS = "not_implemented"

PLACEHOLDERS = (
    "dms_inventory_stub",
    "oem_incentive_stub",
    "deal_jacket_vault_stub",
)


def connector_status(name: str) -> dict:
    return {"name": name, "status": STATUS, "implemented": False}
