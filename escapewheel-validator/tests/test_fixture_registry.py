"""The fixture's registry stands in for core, so it declares no resource core lacks."""

import json
from pathlib import Path

import pytest

from .conftest import read_registry

REGISTRY = Path(__file__).resolve().parents[2] / "spec" / "artifacts" / "logical_schemas.json"


@pytest.mark.skipif(not REGISTRY.is_file(), reason="the specification's tree is not beside this package")
def test_the_fixture_registry_declares_only_resources_core_declares(packet_root):
    """A test that needs another resource declares it itself, or in an extension of its own."""
    core = json.loads(REGISTRY.read_text())["resources"]
    assert sorted(set(read_registry(packet_root)["resources"]) - set(core)) == []
