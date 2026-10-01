"""Sources are ordered by what each consumes."""

from __future__ import annotations

import pytest

from escapewheel_writer.errors import (
    SourcesNotOrdered,
)
from escapewheel_writer.recipe import Recipe
from escapewheel_writer.sources import ADAPTERS
from escapewheel_writer.sourcing import order
from tests.builders import write_recipe


def test_sources_order_after_what_they_consume(tmp_path, registry):
    body = (
        '\n[[source]]\nkind = "waveforms"\nroot = "."\nowns = []\n'
        '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = []\n'
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'
    )
    ordered = [s.kind for s in order(Recipe.load(write_recipe(tmp_path, body)))]
    # Both consume the sorter's units and neither consumes the other: the waveform source names a
    # contact from the electrode table it opens itself, and the writer resolves the name (Part 05
    # §8), so nothing makes it wait for the NWB.
    assert ordered.index("sorter") < ordered.index("nwb")
    assert ordered.index("sorter") < ordered.index("waveforms")


def test_a_source_consuming_an_undeclared_kind_is_refused(tmp_path):
    """`NWBSource` needs the sorter's units to attach a unit to an electrode."""
    body = '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = []\n'
    with pytest.raises(SourcesNotOrdered) as refused:
        order(Recipe.load(write_recipe(tmp_path, body)))
    assert (refused.value.kinds, refused.value.missing) == (("nwb",), ("sorter",))


def test_a_dependency_cycle_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(ADAPTERS["sorter"], "CONSUMES", ("nwb",))
    body = '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = []\n\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'
    with pytest.raises(SourcesNotOrdered) as refused:
        order(Recipe.load(write_recipe(tmp_path, body)))
    assert (refused.value.kinds, refused.value.missing) == (("nwb", "sorter"), ())
