"""The accessors as compositions: what they return equals mapping every row and cutting after."""

import json

import pyarrow as pa
import pytest
from packet_fixture import CLOCK_BEHAVIOUR, CLOCK_PROBE, UNITS, resource_entry, write_table

from escapewheel_reader import (
    STORED,
    attach_clocks,
    events,
    intervals,
    on_clock,
    open_packet,
    seconds,
    spike_times,
    units,
    where,
)

SPANS = [(1_000_000, 1_000_000), (1_031_250, 1_100_000), (900_000, 1_050_001), (1_200_000, 1_300_000), (0, 10)]
SPIKE_ORDER = [("unit_id", "ascending"), ("t_tick", "ascending")]


def _mapped_then_cut(packet, resource_id, span, columns):
    """Every row read, mapped onto the reference clock, then cut: what the accessors computed before."""
    table = attach_clocks(packet, packet.table(resource_id, columns=columns), resource_id)
    table = on_clock(packet, table)
    return table if span is None else table.filter(where(t_tick=span))


@pytest.fixture
def dense_packet(dense_root):
    return open_packet(dense_root)


@pytest.mark.parametrize("span", [None, *SPANS])
def test_spike_times_equal_mapping_every_spike_then_cutting(dense_packet, span):
    expected = _mapped_then_cut(dense_packet, "core.spike_events", span, ["unit_id", "t_tick"])
    expected = expected.select(["unit_id", "t_tick", "clock_id"])
    found = spike_times(dense_packet, units=units(dense_packet), t_tick=span)
    assert found.equals(expected)
    one = spike_times(dense_packet, UNITS[0], t_tick=span)
    assert one.replace_schema_metadata().equals(expected.filter(where(unit_id=UNITS[0])))


@pytest.mark.parametrize("span", [None, *SPANS])
def test_events_equal_mapping_every_event_then_cutting(dense_packet, span):
    expected = _mapped_then_cut(dense_packet, "core.events", span, None)
    assert events(dense_packet, t_tick=span).equals(expected)


@pytest.mark.parametrize("span", SPANS)
def test_a_coordinate_constraint_with_on_clock_applies_on_the_output_clock(dense_packet, span):
    expected = _mapped_then_cut(dense_packet, "core.spike_events", span, None)
    found = dense_packet.table("core.spike_events", on_clock=True, t_tick=span)
    assert found.equals(expected)


def test_a_coordinate_constraint_without_on_clock_applies_to_stored_ticks(dense_packet):
    stored = dense_packet.table("core.spike_events", t_tick=(0, 10))
    assert stored.column("t_tick").to_pylist() == [4]


def test_intervals_and_units_come_back_on_the_reference_clock(dense_packet):
    mapped = intervals(dense_packet)
    assert set(mapped.column("clock_id").to_pylist()) == {CLOCK_BEHAVIOUR}
    assert mapped.equals(on_clock(dense_packet, dense_packet.table("core.intervals"), resource_id="core.intervals"))
    assert intervals(dense_packet, clock=STORED).equals(dense_packet.table("core.intervals"))
    stored = dense_packet.table("core.units")
    assert units(dense_packet).equals(on_clock(dense_packet, stored, resource_id="core.units"))
    assert units(dense_packet, clock=STORED).equals(stored)


def test_intervals_take_seconds_per_coordinate(dense_packet):
    found = intervals(dense_packet, seconds=True)
    expected = seconds(dense_packet, intervals(dense_packet), resource_id="core.intervals")
    assert found.equals(expected)
    assert {"start_second", "stop_second"} <= set(found.column_names)


@pytest.fixture
def routed_packet(dense_root):
    """`dense_root` carrying `analysis.spike_events` as a writer maps it: core's spikes on the reference clock."""
    packet = open_packet(dense_root)
    mapped = on_clock(packet, packet.table("core.spike_events"), resource_id="core.spike_events")
    analysis = mapped.select(["session_id", "unit_id", "t_tick", "clock_id"]).sort_by(
        [("t_tick", "ascending"), ("unit_id", "ascending")]
    )
    manifest = json.loads((dense_root / "packet.json").read_text())
    by_id = {r["resource_id"]: r for r in manifest["resources"]}
    uri = write_table(dense_root, "analysis_spike_events", analysis)
    if "analysis.spike_events" in by_id:
        by_id["analysis.spike_events"]["uri"] = uri
    else:
        manifest["resources"].append(resource_entry("analysis.spike_events", uri))
    (dense_root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packet(dense_root)


@pytest.mark.parametrize("span", [None, *SPANS])
def test_spikes_on_the_reference_clock_are_read_from_the_mapped_table(routed_packet, span, monkeypatch):
    expected = _mapped_then_cut(routed_packet, "core.spike_events", span, ["unit_id", "t_tick"])
    expected = expected.select(["unit_id", "t_tick", "clock_id"]).sort_by(SPIKE_ORDER)
    scanned = []
    original = type(routed_packet).scan
    monkeypatch.setattr(type(routed_packet), "scan", lambda self, rid: scanned.append(rid) or original(self, rid))
    found = spike_times(routed_packet, units=units(routed_packet), t_tick=span)
    assert scanned == ["analysis.spike_events"]
    assert found.sort_by(SPIKE_ORDER).equals(expected)


def test_spikes_on_another_clock_or_as_stored_still_read_core(routed_packet):
    stored = spike_times(routed_packet, UNITS[0], clock=STORED)
    assert set(stored.column("clock_id").to_pylist()) == {CLOCK_PROBE}
    on_probe = spike_times(routed_packet, UNITS[0], clock=CLOCK_PROBE)
    assert on_probe.column("t_tick").equals(stored.column("t_tick"))


def test_routed_seconds_equal_mapped_seconds(routed_packet):
    found = spike_times(routed_packet, units=units(routed_packet), seconds=True).sort_by(SPIKE_ORDER)
    mapped = _mapped_then_cut(routed_packet, "core.spike_events", None, ["unit_id", "t_tick"])
    expected = seconds(routed_packet, mapped.select(["unit_id", "t_tick", "clock_id"])).sort_by(SPIKE_ORDER)
    assert found.equals(expected)


def test_a_composite_selection_is_exact_on_either_route(routed_packet):
    chosen = pa.table({"unit_id": pa.array([UNITS[0], UNITS[2]], pa.int32())})
    for clock in (None, STORED):
        found = spike_times(routed_packet, units=chosen, clock=clock)
        assert set(found.column("unit_id").to_pylist()) == {UNITS[0], UNITS[2]}
