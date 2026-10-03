"""A range on one clock, inverted onto the ticks each table stores."""

import numpy as np
import pyarrow as pa
import pytest
from packet_fixture import CLOCK_BEHAVIOUR, CLOCK_PROBE

from escapewheel_reader import open_packet, tick_bounds, tick_range
from escapewheel_reader.clocks import ClockGraph, attach_clocks, clock_graph, declared_bound, mapped, stored_intervals

#: Stored ticks every random graph is checked over: past both ends of every anchor sequence drawn.
TICKS = np.arange(-40_000, 40_000, dtype=np.int64)


def _graph(rng):
    """A chain of one to three hops above clock 1, each hop anchors or a linear transform."""
    hops = int(rng.integers(1, 4))
    parents, anchors, transforms = {}, {}, {}
    for child in range(2, hops + 2):
        parents[child] = child - 1
        if rng.random() < 0.6:
            size = int(rng.integers(3, 30))
            gaps = rng.integers(1, 200, size - 1)
            if rng.random() < 0.5:
                gaps[rng.integers(0, size - 1)] *= 20  # wider than the bound reaches, so a hole
            anchor_t = np.concatenate([[rng.integers(-500, 500)], gaps]).cumsum()
            anchor_p = np.concatenate([[rng.integers(-500, 500)], rng.integers(1, 400, size - 1)]).cumsum()
            anchors[child] = (anchor_t.astype(np.int64), anchor_p.astype(np.int64))
        else:
            transforms[child] = (float(rng.choice([1 / 3, 0.37, 1.0, 2.5, 30.0])), float(rng.uniform(-300, 300)))
    return ClockGraph(parents, anchors, transforms), hops + 1


def _selected(starts, stops):
    selected = np.zeros(TICKS.size, dtype=bool)
    for start, stop in zip(starts, stops, strict=True):
        selected |= (TICKS >= start) & (TICKS <= stop)
    return selected


@pytest.mark.parametrize("seed", range(40))
def test_the_inverse_selects_exactly_the_ticks_mapping_places_in_range(seed):
    rng = np.random.default_rng(seed)
    graph, leaf = _graph(rng)
    bound = float(rng.choice([0.5, 1.0, 1.7, 3.0]))
    for target in range(1, leaf + 1):
        lo, hi = sorted(rng.integers(-20_000, 40_000, 2).tolist())
        for span in ((lo, hi), (lo, lo)):
            for clock in range(target, leaf + 1):
                batch = pa.record_batch({"t_tick": TICKS, "clock_id": np.full(TICKS.size, clock, np.int32)})
                parent, placed = mapped(batch, target, graph, bound)
                expected = placed & (parent >= span[0]) & (parent <= span[1])
                found = _selected(*stored_intervals(graph, clock, target, span, bound))
                assert (found == expected).all(), (clock, target, span)


def test_anchors_that_do_not_increase_refuse_the_inverse():
    graph = ClockGraph({2: 1}, {2: (np.array([0, 10, 5]), np.array([0, 10, 20]))}, {})
    with pytest.raises(ValueError, match="do not increase"):
        stored_intervals(graph, 2, 1, (0, 10), 1.0)


@pytest.fixture
def dense_packet(dense_root):
    return open_packet(dense_root)


def _in_span(packet, resource_id, column, clock_column, span):
    """The rows whose `column` mapping places in `span`, found by mapping every row."""
    table = attach_clocks(packet, packet.table(resource_id), resource_id).combine_chunks()
    batch = pa.record_batch({"t_tick": table.column(column).chunk(0), "clock_id": table.column(clock_column).chunk(0)})
    parent, placed = mapped(batch, CLOCK_BEHAVIOUR, clock_graph(packet), declared_bound(packet))
    return table.filter(pa.array(placed & (parent >= span[0]) & (parent <= span[1])))


SPANS = [(1_000_000, 1_000_000), (1_031_250, 1_100_000), (900_000, 1_050_001), (1_200_000, 1_300_000), (0, 10)]


@pytest.mark.parametrize("span", SPANS)
def test_a_range_on_spikes_selects_by_unit_exactly_what_mapping_keeps(dense_packet, span):
    """Spikes reach their clock through `core.units`, so each clock's term tests the unit."""
    expected = _in_span(dense_packet, "core.spike_events", "t_tick", "clock_id", span)
    found = dense_packet.scan("core.spike_events").to_table(filter=tick_range(dense_packet, "core.spike_events", span))
    columns = ["unit_id", "t_tick"]
    order = [(name, "ascending") for name in columns]
    assert found.select(columns).sort_by(order).equals(expected.select(columns).sort_by(order))


@pytest.mark.parametrize("span", SPANS)
@pytest.mark.parametrize("column", ["start_tick", "stop_tick"])
def test_a_range_on_a_table_carrying_its_clock_tests_each_clock_in_turn(dense_packet, span, column):
    expected = _in_span(dense_packet, "core.intervals", column, "clock_id", span)
    found = dense_packet.scan("core.intervals").to_table(
        filter=tick_range(dense_packet, "core.intervals", span, column=column)
    )
    assert sorted(found.column("interval_id").to_pylist()) == sorted(expected.column("interval_id").to_pylist())


def test_a_table_with_two_coordinates_needs_one_named(dense_packet):
    with pytest.raises(ValueError, match="name one as column"):
        tick_range(dense_packet, "core.intervals", (0, 1))


def test_the_bounds_are_the_intervals_the_expression_tests(dense_packet):
    """Probe ticks 0 to 30,000 land on 1,000,000 to 1,031,250; the reference clock's own range is itself."""
    bounds = tick_bounds(dense_packet, "core.spike_events", (1_000_000, 1_031_250))
    assert bounds.sort_by("clock_id").to_pylist() == sorted(
        [
            {"clock_id": CLOCK_PROBE, "lo": 0, "hi": 30_000},
            {"clock_id": CLOCK_BEHAVIOUR, "lo": 1_000_000, "hi": 1_031_250},
        ],
        key=lambda row: row["clock_id"],
    )


def test_an_empty_range_matches_nothing(dense_packet):
    expression = tick_range(dense_packet, "core.spike_events", (5, 4))
    assert dense_packet.scan("core.spike_events").count_rows(filter=expression) == 0
