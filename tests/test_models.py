"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


def test_every_model_round_trips():
    from app import store
    from app.models import MODELS

    assert MODELS
    for cap_id, cls in MODELS.items():
        blank = cls.from_dict({})
        assert blank.to_dict()["id"] is None
        saved = store.save(cap_id, {"reference": "sample", "status": "open"})
        assert saved["id"] is not None
        fetched = store.get(cap_id, saved["id"])
        assert fetched is not None
        assert fetched["reference"] == "sample"


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
