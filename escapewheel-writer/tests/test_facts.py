"""A preference between sources discards no fact the other states."""

from __future__ import annotations

import pytest

from escapewheel_writer.errors import (
    SourceDefect,
    SourceFault,
)
from escapewheel_writer.facts import refuse_a_discarded_fact
from escapewheel_writer.session import Context
from tests.builders import contested_recipe

# -- R108: a preference discards no stated fact --------------------------------------------


class _Registry:
    """Enough of a writer to answer what a table declares."""

    def __init__(self, registry):
        self._registry = registry

    def spec(self, resource_id):
        declaration = self._registry["resources"].get(resource_id)
        return None if declaration is None or declaration["kind"] != "table" else declaration["table"]


def test_a_resource_the_recipe_prefers_nothing_for_is_not_compared(tmp_path, registry):
    """Where the rows are disjoint there is no passed-over row to weigh (Part 05 §3.4).

    A sync source's reference clock and a sorter's probe clocks are different rows of one table,
    so comparing them would report a loss that is not one.
    """
    context = Context(session_id="s001")
    context.stated["core.clocks"] = {
        "sync": [{"clock_id": "harp", "tick_rate_num": 31250}],
        "sorter": [{"clock_id": "probeA", "tick_rate_num": 30000}],
    }
    refuse_a_discarded_fact(_Registry(registry), context, contested_recipe(tmp_path))


def test_a_preference_that_discards_a_stated_fact_is_refused(tmp_path, registry):
    """Part 05 §3.4: the premise a preference buys silence on is now checked."""
    context = Context(session_id="s001")
    context.stated["core.probes"] = {
        "nwb": [{"probe_id": "probeA", "probe_type": None}],
        "sorter": [{"probe_id": "probeA", "probe_type": "NP2000"}],
    }
    with pytest.raises(SourceDefect) as refused:
        refuse_a_discarded_fact(_Registry(registry), context, contested_recipe(tmp_path))
    assert refused.value.code is SourceFault.FACT_DISCARDED
    assert "core.probes.probe_type" in str(refused.value)


def test_a_preferred_source_that_stages_nothing_is_refused(tmp_path, registry):
    """Part 05 §3.4's limiting case: every value discarded, not just one."""
    context = Context(session_id="s001")
    context.stated["core.probes"] = {"sorter": [{"probe_id": "probeA"}]}
    context.stated["core.probes"]["nwb"] = []
    with pytest.raises(SourceDefect) as refused:
        refuse_a_discarded_fact(_Registry(registry), context, contested_recipe(tmp_path))
    assert refused.value.code is SourceFault.FACT_DISCARDED
    assert "staged none" in str(refused.value)


def test_two_sources_that_agree_are_not_refused(tmp_path, registry):
    """Agreement is the ordinary case, and `metadata` is never compared (Part 05 §3.4)."""
    context = Context(session_id="s001")
    context.stated["core.probes"] = {
        "nwb": [{"probe_id": "probeA", "probe_type": "NP2000", "metadata": '{"a": 1}'}],
        "sorter": [{"probe_id": "probeA", "probe_type": "NP2000", "metadata": '{"b": 2}'}],
    }
    refuse_a_discarded_fact(_Registry(registry), context, contested_recipe(tmp_path))
