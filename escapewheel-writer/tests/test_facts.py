"""A preference between sources discards no fact the other states, unless a column override says so."""

from __future__ import annotations

import pytest

from escapewheel_writer import PacketWriter
from escapewheel_writer.errors import (
    SourceDefect,
    SourceFault,
)
from escapewheel_writer.facts import refuse_a_discarded_fact
from escapewheel_writer.notes import NoteCode, coded
from escapewheel_writer.session import Context
from tests.builders import contested_recipe

# -- a preference discards no stated fact --------------------------------------------------


def _writer(registry):
    """A writer for one session, which fills `session_id` and owned names as staging does."""
    return PacketWriter(registry, packet_id="s001", session="s001")


def _overriding(tmp_path, *entries, prefer=None):
    """The contested recipe carrying `[overrides]` entries, each `(key, reason)`."""
    lines = "".join(f'"{key}" = "{reason}"\n' for key, reason in entries)
    return contested_recipe(tmp_path, "\n[overrides]\n" + lines, prefer=prefer)


def _prefer(resource, kind):
    return f'\n[preference."{resource}"]\nsource = "{kind}"\nreason = "it knows more"\n'


def _probes(context, nwb, sorter):
    context.stated["core.probes"] = {"nwb": nwb, "sorter": sorter}


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
    refuse_a_discarded_fact(_writer(registry), context, contested_recipe(tmp_path))


def test_a_preference_that_discards_a_stated_fact_is_refused(tmp_path, registry):
    """Part 05 §3.4: the premise a preference buys silence on is now checked."""
    context = Context(session_id="s001")
    _probes(context, [{"probe_id": "probeA", "probe_type": None}], [{"probe_id": "probeA", "probe_type": "NP2000"}])
    with pytest.raises(SourceDefect) as refused:
        refuse_a_discarded_fact(_writer(registry), context, contested_recipe(tmp_path))
    assert refused.value.code is SourceFault.FACT_DISCARDED
    assert "core.probes.probe_type" in str(refused.value)
    assert "resource.column" in str(refused.value)


def test_a_preferred_source_that_stages_nothing_is_refused(tmp_path, registry):
    """Part 05 §3.4's limiting case: every value discarded, not just one."""
    context = Context(session_id="s001")
    _probes(context, [], [{"probe_id": "probeA"}])
    with pytest.raises(SourceDefect) as refused:
        refuse_a_discarded_fact(_writer(registry), context, contested_recipe(tmp_path))
    assert refused.value.code is SourceFault.FACT_DISCARDED
    assert "staged none" in str(refused.value)


def test_two_sources_that_agree_are_not_refused(tmp_path, registry):
    """Agreement is the ordinary case, and `metadata` is never compared (Part 05 §3.4)."""
    context = Context(session_id="s001")
    _probes(
        context,
        [{"probe_id": "probeA", "probe_type": "NP2000", "metadata": '{"a": 1}'}],
        [{"probe_id": "probeA", "probe_type": "NP2000", "metadata": '{"b": 2}'}],
    )
    refuse_a_discarded_fact(_writer(registry), context, contested_recipe(tmp_path))


# -- a column override releases a null column of a corresponding row ---------------------------


def test_a_column_override_releases_the_null_column_and_reports_it(tmp_path, registry):
    """Part 05 §3.4: the preferred row is kept as delivered, and §3.6 reports the release."""
    context = Context(session_id="s001")
    preferred = [{"probe_id": "probeA", "probe_type": None}]
    _probes(context, preferred, [{"probe_id": "probeA", "probe_type": "NP2000"}])
    recipe = _overriding(tmp_path, ("core.probes.probe_type", "the sorter guesses the type from the stream"))
    refuse_a_discarded_fact(_writer(registry), context, recipe)
    assert preferred == [{"probe_id": "probeA", "probe_type": None}]
    (released,) = coded(context.notes, NoteCode.VALUE_RELEASED)
    assert "core.probes.probe_type" in released and "sorter" in released
    assert "guesses the type" in released


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(("core.probes.manufacturer", "another column"), id="another-column"),
        pytest.param(("subject.subject_id", "a field"), id="a-field-override"),
    ],
)
def test_an_override_of_anything_but_the_column_still_refuses(tmp_path, registry, entry):
    """Part 05 §3.4: a release reaches the named column only, and a field override releases none (§3.6)."""
    context = Context(session_id="s001")
    _probes(context, [{"probe_id": "probeA", "probe_type": None}], [{"probe_id": "probeA", "probe_type": "NP2000"}])
    with pytest.raises(SourceDefect, match=r"core\.probes\.probe_type"):
        refuse_a_discarded_fact(_writer(registry), context, _overriding(tmp_path, entry))


@pytest.mark.parametrize(
    ("nwb", "sorter", "said"),
    [
        pytest.param([{"probe_id": "probeB"}], [{"probe_id": "probeA"}], "did not", id="a-row-not-produced"),
        pytest.param([], [{"probe_id": "probeA"}], "staged none", id="no-preferred-rows"),
        pytest.param(
            [{"probe_id": "probeA"}], [{"probe_id": None, "probe_type": "NP2000"}], "did not", id="a-null-key"
        ),
    ],
)
def test_a_column_override_releases_no_row(tmp_path, registry, nwb, sorter, said):
    """Part 05 §3.4: a dropped row, an empty preferred source and a null key refuse whatever the recipe overrides."""
    context = Context(session_id="s001")
    _probes(context, nwb, sorter)
    with pytest.raises(SourceDefect, match=said):
        refuse_a_discarded_fact(_writer(registry), context, _overriding(tmp_path, ("core.probes.probe_type", "why")))


def test_a_passed_over_row_with_a_null_key_is_refused_without_an_override(tmp_path, registry):
    """Part 05 §3.4: a row with a null in a key column corresponds to no row."""
    context = Context(session_id="s001")
    _probes(context, [{"probe_id": None}], [{"probe_id": None}])
    with pytest.raises(SourceDefect, match="did not"):
        refuse_a_discarded_fact(_writer(registry), context, contested_recipe(tmp_path))


@pytest.mark.parametrize(
    ("winner", "released"),
    [pytest.param("nwb", "probe_type", id="prefer-nwb"), pytest.param("sorter", "manufacturer", id="prefer-sorter")],
)
def test_each_source_holding_a_column_the_other_lacks_builds_under_either_preference(
    tmp_path, registry, winner, released
):
    """Part 05 §3.4: one column override resolves what no choice of source did."""
    context = Context(session_id="s001")
    _probes(
        context,
        [{"probe_id": "probeA", "manufacturer": "IMEC", "probe_type": None}],
        [{"probe_id": "probeA", "manufacturer": None, "probe_type": "NP2000"}],
    )
    recipe = _overriding(
        tmp_path, (f"core.probes.{released}", "the other source states it"), prefer=_prefer("core.probes", winner)
    )
    refuse_a_discarded_fact(_writer(registry), context, recipe)
    assert coded(context.notes, NoteCode.VALUE_RELEASED)


def test_a_column_staging_fills_is_compared_filled(tmp_path, registry):
    """Part 05 §3.4: a `session_id` or owned name the writer fills is no loss, so its override is idle (§3.6)."""
    context = Context(session_id="s001")
    _probes(context, [{"probe_id": "probeA"}], [{"probe_id": "probeA", "session_id": "s001", "probe_name": "probeA"}])
    recipe = _overriding(tmp_path, ("core.probes.probe_name", "the writer fills it"))
    refuse_a_discarded_fact(_writer(registry), context, recipe)
    (idle,) = coded(context.notes, NoteCode.COLUMN_OVERRIDE_IDLE)
    assert idle.startswith("warning:") and "core.probes.probe_name" in idle
    assert not coded(context.notes, NoteCode.VALUE_RELEASED)


def test_a_key_holding_session_id_corresponds_once_filled(tmp_path, registry):
    """Part 05 §3.4: a source omitting the `session_id` in a key still delivers the row the other does."""
    context = Context(session_id="s001")
    context.stated["core.coordinate_frames"] = {
        "nwb": [{"coordinate_frame": "ccf", "atlas": "CCF"}],
        "sorter": [{"session_id": "s001", "coordinate_frame": "ccf", "atlas": "CCF"}],
    }
    recipe = contested_recipe(tmp_path, _prefer("core.coordinate_frames", "nwb"))
    refuse_a_discarded_fact(_writer(registry), context, recipe)


@pytest.mark.parametrize(
    ("second", "refuses"),
    [pytest.param(None, False, id="both-null"), pytest.param("NP1000", True, id="one-states-it")],
)
def test_a_repeated_preferred_key_releases_only_where_every_row_leaves_it_null(tmp_path, registry, second, refuses):
    """Part 05 §3.4: each preferred row of a key corresponds, and a release never chooses among them."""
    context = Context(session_id="s001")
    _probes(
        context,
        [{"probe_id": "probeA", "probe_type": None}, {"probe_id": "probeA", "probe_type": second}],
        [{"probe_id": "probeA", "probe_type": "NP2000"}],
    )
    recipe = _overriding(tmp_path, ("core.probes.probe_type", "why"))
    if refuses:
        with pytest.raises(SourceDefect, match="1 of 2 rows"):
            refuse_a_discarded_fact(_writer(registry), context, recipe)
    else:
        refuse_a_discarded_fact(_writer(registry), context, recipe)
        assert coded(context.notes, NoteCode.VALUE_RELEASED)
