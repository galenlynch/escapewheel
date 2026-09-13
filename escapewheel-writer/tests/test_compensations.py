"""What the importer assumes about its sources, recorded rather than assumed."""

import pytest

from escapewheel_writer.sources.compensations import COMPENSATIONS, Compensates, describe


def test_every_registered_compensation_carries_its_evidence():
    """The registry is a record of measured faults, not a place to park a guess."""
    for identifier, entry in COMPENSATIONS.items():
        assert entry.defect and entry.action and entry.evidence, identifier
        assert "inventory/" in entry.evidence, f"{identifier} cites no measurement"


def test_an_unregistered_compensation_is_refused():
    class Adapter(Compensates):
        pass

    a = Adapter()
    with pytest.raises(KeyError, match="not a registered compensation"):
        a.compensate("something.i.just.made.up")


def test_declaring_one_twice_records_it_once():
    class Adapter(Compensates):
        pass

    a = Adapter()
    a.compensate("lfp.timestamps_distrusted")
    a.compensate("lfp.timestamps_distrusted")
    assert a.compensations == ["lfp.timestamps_distrusted"]


def test_describe_renders_what_a_packet_carries():
    rendered = describe(["lfp.timestamps_distrusted", "lfp.timestamps_distrusted"])
    assert [e["id"] for e in rendered] == ["lfp.timestamps_distrusted"]
    assert "268 days" in rendered[0]["defect"]


def test_a_knowing_pass_through_is_registered_too():
    """Choosing not to correct is as much an assumption as choosing to."""
    assert "nwb.stored_offset_kept" in COMPENSATIONS
    assert "kept" in COMPENSATIONS["nwb.stored_offset_kept"].action


def test_the_lfp_source_declares_what_it_ignores(tmp_path):
    """It never reads the stored timestamps, and the packet should say so."""
    from tests.test_lfp import RATES, _contacts, _series, _source

    root = tmp_path / "s.nwb"
    _series(root)
    _contacts(root)
    source = _source(root)
    source.records(rates=RATES)
    assert source.compensations == ["lfp.timestamps_distrusted"]


def test_the_nwb_source_declares_an_offset_it_kept(tmp_path):
    """The -07:53 on a date of birth is Pacific Local Mean Time, and it is kept as stored."""
    from zoneinfo import ZoneInfo

    from escapewheel_writer import Clock
    from escapewheel_writer.clock import HARP_TICK_RATE_HZ
    from escapewheel_writer.sources import NWBSource
    from tests import nwbfixture

    root = nwbfixture.build(tmp_path)
    nwbfixture.text(root / "general/subject/date_of_birth", ["2024-09-24T00:00:00-07:53"])
    clock = Clock(
        "harp", session_id="mini_2025-04-09", name="HARP", tick_rate_num=HARP_TICK_RATE_HZ, origin="HARP epoch"
    )
    source = NWBSource(root, clock=clock, zone=ZoneInfo("America/Los_Angeles"), units={})
    source.subjects()
    assert "nwb.stored_offset_kept" in source.compensations


def test_strict_refuses_a_build_that_worked_around_something(tmp_path, registry):
    """Every note is a place the packet says less than the source could have."""
    from escapewheel_writer.recipe import Recipe
    from escapewheel_writer.session import RecipeError, build
    from tests import sorterfixture

    root = sorterfixture.build(tmp_path)
    path = tmp_path / "session.toml"
    path.write_text(f"""
[packet]
id = "s1"
registry = "r"
[session]
session_id = "s1"
reference_clock_id = "harp"
[[clock]]
clock_id = "harp"
name = "HARP"
tick_rate_num = 31250
origin = "e"
[[source]]
kind = "sorter"
root = "{root}"
owns = ["core.units"]
""")
    recipe = Recipe.load(path)
    assert build(recipe, registry)  # the same build passes without the flag
    with pytest.raises(RecipeError, match=r"note\(s\) under --strict"):
        build(recipe, registry, strict=True)
