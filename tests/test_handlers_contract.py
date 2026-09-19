"""Every capability handler is loadable and dispatches its declared blocks."""

from __future__ import annotations

import importlib

import pytest

from app.jobs import CAPABILITIES

CAPABILITY_IDS = sorted(item["id"] for item in CAPABILITIES)


@pytest.mark.parametrize("capability_id", CAPABILITY_IDS)
def test_handler_exports_its_contract(capability_id):
    module = importlib.import_module("app.actions." + capability_id)
    assert module.CAPABILITY_ID == capability_id
    assert module.ENTITY
    assert module.BLOCK_IDS, "a capability with no bound block is not a capability"
    assert module.CAPABILITY_FIELDS
    missing = [block for block in module.BLOCK_IDS if block not in module.BLOCK_DEFAULT_ACTIONS]
    assert not missing, f"no default action for {missing}"


def _typed_sample(cls):
    """Same construction rule the factory harness uses for a schema sample."""
    out = {}
    for name in cls.FIELDS:
        rules = (getattr(cls, "CONSTRAINTS", {}) or {}).get(name, {})
        allowed = rules.get("allowed_values")
        kind = str(getattr(cls, "__annotations__", {}).get(name, "str")).strip()
        if allowed:
            out[name] = allowed[0]
        elif kind == "int":
            out[name] = int(rules.get("min", 1))
        elif kind == "float":
            out[name] = float(rules.get("min", 1.0))
        elif kind == "bool":
            out[name] = False
        else:
            out[name] = "sample"
    return out


@pytest.mark.parametrize("capability_id", CAPABILITY_IDS)
def test_handle_returns_a_mapping(capability_id):
    from app.models import MODELS

    module = importlib.import_module("app.actions." + capability_id)
    result = module.handle(_typed_sample(MODELS[capability_id]))
    assert isinstance(result, dict)
    assert result.get("capability") == capability_id
    for block_id in module.BLOCK_IDS:
        assert block_id in result["results"], f"{block_id} was never invoked"


def test_handlers_do_not_import_the_http_surface():
    """A handler must not import app.routes / app.main / the actions package."""
    import pathlib
    import re

    offending = []
    for path in sorted(pathlib.Path("app/actions").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if re.search(r"from app\.(routes|main) import|import app\.(routes|main)\b", source):
            offending.append(path.name)
        if re.search(r"from app\.actions import", source):
            offending.append(path.name)
    assert not offending
