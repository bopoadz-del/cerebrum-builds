"""Honest placeholder connectors. Smart-home/IoT is not_implemented."""

STATUS = "not_implemented"

PLACEHOLDERS = (
    "cmms_stub",
    "iot_stub",
    "document_vault_stub",
    "smart_home_placeholder",
)


def connector_status(name: str) -> dict:
    return {"name": name, "status": STATUS, "implemented": False}
