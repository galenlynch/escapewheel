"""Each shipped adapter has the capabilities a build tests it for."""

import pytest

from escapewheel_writer.protocols import ReferencesArrays, ReferencesMedia, ReferencesResources, StagesArrays, Streams
from escapewheel_writer.reading import Delivered
from escapewheel_writer.sources import ADAPTERS

CAPABLE = {
    Streams: {"sorter"},
    StagesArrays: {"harp", "nwb", "waveforms"},
    ReferencesArrays: {"lfp"},
    ReferencesMedia: set(),
    ReferencesResources: {"sidecars"},
}


@pytest.mark.parametrize("capability", CAPABLE, ids=lambda capability: capability.__name__)
def test_a_capability_is_had_by_the_adapters_that_declare_its_members(capability):
    assert {kind for kind, adapter in ADAPTERS.items() if issubclass(adapter, capability)} == CAPABLE[capability]


@pytest.mark.parametrize("capability", CAPABLE, ids=lambda capability: capability.__name__)
def test_a_delivered_source_has_every_capability_a_delivery_carries(capability):
    assert issubclass(Delivered, capability)


@pytest.mark.parametrize("kind", sorted(ADAPTERS))
def test_every_adapter_has_the_members_a_build_asks_of_each(kind):
    adapter = ADAPTERS[kind]
    assert all(callable(getattr(adapter, member, None)) for member in ("records", "offers"))
    assert isinstance(adapter.STATES, dict)
    assert isinstance(adapter.PRODUCES, (set, frozenset, tuple))
