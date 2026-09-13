"""Honest placeholder connectors. Offline platform — no network callbacks."""

STATUS = "not_implemented"

PLACEHOLDERS = (
    "fleet_registry_feed_stub",
    "maintenance_oem_stub",
    "crew_training_lms_stub",
)


def connector_status(name: str) -> dict:
    return {"name": name, "status": STATUS, "implemented": False}
