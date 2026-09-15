"""Models must survive a round trip through sqlite."""

from app import store
from app.migrations import upgrade_head
from app.models import MODELS


def test_every_model_round_trips():
    upgrade_head()
    assert MODELS, "no models were generated"
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({"reference": "sample", "status": "open"})
        payload = instance.to_dict()
        payload.pop("id", None)
        saved = store.save(cap_id, payload)
        fetched = store.get(cap_id, saved["id"])
        assert fetched is not None
        assert fetched["reference"] == "sample"
        assert fetched["status"] == "open"


def test_models_expose_their_fields():
    assert MODELS, "no models were generated"
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()["id"] is None
        assert cls.FIELDS, cap_id
