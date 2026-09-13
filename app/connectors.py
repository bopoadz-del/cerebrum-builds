"""Honest placeholder connectors. Offline platform — no network callbacks."""

STATUS = "not_implemented"

PLACEHOLDERS = (
    "pims_stub",
    "lab_results_stub",
    "pharmacy_feed_stub",
)


def connector_status(name: str) -> dict:
    return {"name": name, "status": STATUS, "implemented": False}
