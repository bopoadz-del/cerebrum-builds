"""Honest placeholder connectors. Offline platform — no network callbacks."""

STATUS = "not_implemented"

PLACEHOLDERS = (
    "gl_stub",
    "bank_feed_stub",
    "board_pack_vault_stub",
)


def connector_status(name: str) -> dict:
    return {"name": name, "status": STATUS, "implemented": False}
