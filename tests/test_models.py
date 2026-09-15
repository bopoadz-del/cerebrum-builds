"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


def test_every_model_round_trips():


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
