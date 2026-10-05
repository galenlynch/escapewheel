"""Mapping ticks onto a parent clock, and refusing where the mapping is undefined."""

import numpy as np
import pyarrow as pa
import pytest

from escapewheel_reader import ResourceNotFoundError, clocks
from escapewheel_reader.clocks import (
    BOUND,
    ClockGraph,
    _Map,
    align,
    anchors,
    declared_bound,
    extrapolation_error,
    mapped,
    rate,
    stored_intervals,
)
from escapewheel_reader.errors import NotAligned, Unanchored

AP, HARP = 30000, 31250

#: Eight anchors one second apart, a probe counting at 30 kHz against HARP's 31,250.
ANCHOR_T = np.arange(8, dtype=np.int64) * AP + 1000
ANCHOR_P = np.arange(8, dtype=np.int64) * HARP + 553_191_712_312


def test_an_anchor_maps_to_its_own_parent():
    parent, defined = align(ANCHOR_T, ANCHOR_T, ANCHOR_P)
    assert defined.all()
    assert parent.tolist() == ANCHOR_P.tolist()


def test_a_midpoint_interpolates():
    """Half a second along a one-second segment is half a HARP second on."""
    midpoint = np.array([ANCHOR_T[0] + AP // 2], dtype=np.int64)
    parent, defined = align(midpoint, ANCHOR_T, ANCHOR_P)
    assert defined.all()
    assert parent[0] == ANCHOR_P[0] + HARP // 2


def test_order_does_not_matter():
    shuffled = ANCHOR_T[::-1]
    parent, _ = align(shuffled, ANCHOR_T, ANCHOR_P)
    assert parent.tolist() == ANCHOR_P[::-1].tolist()


# -- the bound ------------------------------------------------------------------------


def test_just_before_the_first_anchor_is_defined():
    """A free-running pulse leaves under one interval unanchored at each end, so this is
    the case the bound exists to cover rather than an edge of it."""
    before = np.array([ANCHOR_T[0] - AP + 1], dtype=np.int64)
    parent, defined = align(before, ANCHOR_T, ANCHOR_P)
    assert defined.all()
    assert parent[0] < ANCHOR_P[0]


def test_further_than_one_interval_is_undefined():
    outside = np.array([ANCHOR_T[0] - AP - 1, ANCHOR_T[-1] + AP + 1], dtype=np.int64)
    _, defined = align(outside, ANCHOR_T, ANCHOR_P)
    assert not defined.any()


def test_the_middle_of_a_wide_gap_is_undefined():
    """Part 01 §3.9 applies one threshold both ways: a hole between anchors is the same
    epistemic situation as being past the end."""
    gapped_t = np.array([0, AP, 2 * AP, 20 * AP, 21 * AP, 22 * AP], dtype=np.int64)
    gapped_p = (gapped_t.astype(np.float64) * HARP / AP).astype(np.int64)
    inside = np.array([2 * AP + 100, 11 * AP, 20 * AP - 100], dtype=np.int64)
    _, defined = align(inside, gapped_t, gapped_p)
    assert defined.tolist() == [True, False, True]


def test_a_wider_bound_admits_more():
    outside = np.array([ANCHOR_T[0] - 2 * AP], dtype=np.int64)
    assert not align(outside, ANCHOR_T, ANCHOR_P)[1].any()
    assert align(outside, ANCHOR_T, ANCHOR_P, bound=3.0)[1].all()


# -- which slope extrapolation uses ----------------------------------------------------


def test_extrapolation_uses_the_fitted_rate_not_the_last_segment():
    """The terminal segment's slope comes from two anchors and degrades; the global fit
    does not. A jittered final anchor must not steer the *rate*."""
    jittered = ANCHOR_P.copy()
    jittered[-1] += 400  # one bad edge detection
    beyond = np.array([ANCHOR_T[-1] + AP // 2], dtype=np.int64)
    parent, defined = align(beyond, ANCHOR_T, jittered)
    assert defined.all()
    segment = jittered[-1] + (jittered[-1] - jittered[-2]) // 2
    assert abs(int(parent[0]) - segment) > 100  # not the terminal segment's answer


def test_extrapolation_starts_at_the_terminal_anchor():
    """Part 01 §3.9: the offset is the terminal anchor's parent tick, not a global intercept.

    Displacing every anchor by a constant moves the extrapolation by exactly that constant,
    which is what "anchored at the terminal anchor" means and what an intercept-based
    estimator cannot promise once the sequence is not straight.
    """
    half = AP // 2
    for step in (0, 7919):
        parent, defined = align(np.array([ANCHOR_T[-1] + half], dtype=np.int64), ANCHOR_T, ANCHOR_P + step)
        assert defined.all()
        assert int(parent[0]) == ANCHOR_P[-1] + step + HARP // 2


def test_a_bent_sequence_extrapolates_from_where_it_ended():
    """A clock that wanders leaves a fitted line offset from local truth at the ends, and
    the offset does not shrink with distance."""
    bend = np.rint(200 * np.sin(np.arange(8) * 0.7)).astype(np.int64)
    wandering = ANCHOR_P + bend
    parent, _ = align(np.array([ANCHOR_T[-1] + AP], dtype=np.int64), ANCHOR_T, wandering)
    slope, intercept = rate(ANCHOR_T, wandering)
    # One interval on from the last anchor, at the fitted rate, wherever that anchor sits --
    # which the intercept-based answer misses by the bend the line could not follow.
    assert int(parent[0]) == round(wandering[-1] + slope * AP)
    # The intercept-based answer differs by the last anchor's residual from the line -- an
    # offset that is there at any distance, since both estimators use the same rate.
    residual = wandering[-1] - (slope * ANCHOR_T[-1] + intercept)
    assert round(slope * (ANCHOR_T[-1] + AP) + intercept) == pytest.approx(int(parent[0]) - residual, abs=1)


def test_the_fit_recovers_a_clean_rate():
    slope, _ = rate(ANCHOR_T, ANCHOR_P)
    assert slope == pytest.approx(HARP / AP, rel=1e-12)


def test_the_fit_survives_large_tick_values():
    """HARP anchors run to 5.5e11; fitting on raw values there loses the residual."""
    big_t = ANCHOR_T + 160_000_000
    big_p = ANCHOR_P + 553_000_000_000
    slope, _ = rate(big_t, big_p)
    assert slope == pytest.approx(HARP / AP, rel=1e-9)


# -- what it refuses --------------------------------------------------------------------


def test_too_few_anchors_is_refused():
    """Two anchors give a segment but no median interval worth bounding by."""
    with pytest.raises(Unanchored, match="no median interval"):
        align(ANCHOR_T, ANCHOR_T[:2], ANCHOR_P[:2])


def test_anchors_that_do_not_increase_together_are_refused():
    backwards = ANCHOR_P.copy()
    backwards[4] = backwards[3] - 1
    with pytest.raises(ValueError, match="do not increase together"):
        align(ANCHOR_T, ANCHOR_T, backwards)


def test_an_empty_input_is_empty_output():
    parent, defined = align(np.empty(0, dtype=np.int64), ANCHOR_T, ANCHOR_P)
    assert parent.size == defined.size == 0


# -- scale ------------------------------------------------------------------------------


def test_a_million_ticks_map_without_a_python_loop():
    many = np.sort(np.random.default_rng(0).integers(ANCHOR_T[0], ANCHOR_T[-1], 1_000_000))
    parent, defined = align(many.astype(np.int64), ANCHOR_T, ANCHOR_P)
    assert defined.all()
    assert bool((np.diff(parent) >= 0).all())  # monotone in, monotone out


# -- measuring the bound (Part 01 §3.9) ----------------------------------------------------


def test_a_clean_clock_extrapolates_within_quantization():
    """The estimator on a straight sequence costs rounding and nothing else."""
    measured = extrapolation_error(ANCHOR_T, ANCHOR_P, 1)
    assert measured["n"] == ANCHOR_T.size - 1
    assert measured["max"] <= 1


def test_error_grows_with_the_bend_not_with_the_distance():
    """What costs is the sequence's wander, not how far you reach."""
    wandering = ANCHOR_P + np.rint(300 * np.sin(np.arange(ANCHOR_T.size) * 0.9)).astype(np.int64)
    assert extrapolation_error(ANCHOR_T, wandering, 1)["median"] > extrapolation_error(ANCHOR_T, ANCHOR_P, 1)["median"]


def test_too_few_anchors_measure_nothing():
    assert extrapolation_error(ANCHOR_T[:3], ANCHOR_P[:3], 5) == {}


# -- reading the bound a writer established (Part 02 §12.6) -----------------------------


class _Sessions:
    """A packet stub carrying only what `declared_bound` reads."""

    def __init__(self, *bounds):
        self._table = pa.table({"alignment_bound": pa.array(bounds, pa.float64())})

    def table(self, resource_id, columns=None):
        del resource_id, columns
        return self._table


def test_a_packet_that_says_nothing_maps_at_the_default():
    """A null is read as the default of one median anchor interval."""
    assert declared_bound(_Sessions(None)) == BOUND


def test_the_declared_bound_is_read_from_the_session():
    """The bound is a column of the session, not a key of `core.processing_runs.parameters`."""
    assert declared_bound(_Sessions(2.0)) == 2.0


def test_the_widest_declared_bound_wins():
    """A tick placed under the wider bound stays placed when the packets are read as one."""
    assert declared_bound(_Sessions(3.0, 1.0, None)) == 3.0


def test_an_unreadable_table_is_no_record():
    class _Broken:
        def table(self, resource_id, columns=None):
            raise RuntimeError("no such resource")

    assert declared_bound(_Broken()) == BOUND


def test_a_packet_without_anchors_has_none():
    """`core.clock_anchors` is optional, so its absence is an empty mapping, not an error."""

    class _NoAnchors:
        def table(self, resource_id, columns=None):
            raise ResourceNotFoundError(resource_id)

    assert anchors(_NoAnchors()) == {}


# -- parent chains --------------------------------------------------------------------------

#: Clock 2 is anchored onto the root, clock 1, two root ticks per tick; clock 3 halves onto clock 2
#: by a transform; clock 4 is clock 2's sibling; clock 5 reaches the root by a transform alone.
CHAIN = ClockGraph(
    parents={2: 1, 3: 2, 4: 1, 5: 1},
    anchors={
        2: (np.arange(8, dtype=np.int64) * 1000, 10_000 + np.arange(8, dtype=np.int64) * 2000),
        4: (np.arange(8, dtype=np.int64) * 1000, 10_000 + np.arange(8, dtype=np.int64) * 2000),
    },
    transforms={3: (2.0, 0.0), 5: (2.0, 100.0)},
)


def _on(clock, ticks, target=1):
    batch = pa.record_batch(
        {"t_tick": pa.array(ticks, pa.int64()), "clock_id": pa.array([clock] * len(ticks), pa.int32())}
    )
    return mapped(batch, target, CHAIN, BOUND)


def test_a_tick_climbs_every_clock_in_its_chain():
    """5 on clock 3 is 10 on clock 2, which is 10,020 on the root; reading clock 2's tick as the root's gives 10."""
    parent, keep = _on(3, [5])
    assert keep.tolist() == [True]
    assert parent.tolist() == [10_020]


def test_a_transform_alone_reaches_the_parent():
    parent, keep = _on(5, [10])
    assert (parent.tolist(), keep.tolist()) == ([120], [True])


def test_a_tick_beyond_any_edge_bound_is_not_placed():
    """Clock 3's tick 20,000 is clock 2's 40,000, far past its last anchor at 7,000."""
    _, keep = _on(3, [5, 20_000])
    assert keep.tolist() == [True, False]


def test_ticks_in_chunks_map_as_one_array_does(monkeypatch):
    """Chunks are mapped in place, split where longer than a worker's share, across clocks."""
    monkeypatch.setattr(clocks, "_CHUNK_ROWS", 4)
    lengths = [5, 7, 0, 4]
    ticks = pa.chunked_array([pa.array(np.arange(n, dtype=np.int64) * 600 + 3, pa.int64()) for n in lengths])
    clock = pa.array(np.resize(np.array([2, 2, 3, 5, 5, 5], np.int32), sum(lengths)))
    whole = mapped(pa.record_batch({"t_tick": ticks.combine_chunks(), "clock_id": clock}), 1, CHAIN, BOUND)
    pieces = clocks._pieces(ticks, clock)
    assert [len(piece[1]) for piece in pieces] == [4, 1, 4, 3, 4]
    parent, keep = clocks._mapped(pieces, sum(lengths), 1, CHAIN, BOUND)
    assert (parent.tolist(), keep.tolist()) == (whole[0].tolist(), whole[1].tolist())


def test_a_sibling_clock_is_refused_with_the_way_to_stored_ticks():
    """Clock 4 is not an ancestor of clock 2; reaching it would need an inverse no part defines."""
    with pytest.raises(NotAligned, match="not an ancestor.*clock=STORED"):
        _on(2, [500], target=4)


def test_a_range_inverts_down_a_chain_onto_exactly_the_stored_ticks():
    """Clock 3's tick 5 is clock 2's 10, which lands on 10,020 at the root, and no other tick does."""
    starts, stops = stored_intervals(CHAIN, 3, 1, (10_020, 10_020), 1.0)
    assert (starts.tolist(), stops.tolist()) == ([5], [5])


def test_a_range_beyond_every_anchor_inverts_to_nothing():
    starts, _ = stored_intervals(CHAIN, 2, 1, (10**9, 10**9 + 10), 1.0)
    assert starts.size == 0


@pytest.mark.parametrize("anchor_t", [ANCHOR_T, np.delete(ANCHOR_T, [3, 4])])
def test_placement_matches_the_distance_to_the_nearest_anchor(anchor_t):
    """With or without a hole, inside the anchors and past either end."""
    edge = _Map(anchor_t, ANCHOR_P[: anchor_t.size], BOUND)
    ticks = np.arange(anchor_t[0] - 3 * AP, anchor_t[-1] + 3 * AP, 997, dtype=np.int64)
    _, placed = edge(ticks)
    assert placed.tolist() == (np.interp(ticks, edge.knots, edge.distance) <= edge.span).tolist()
    assert edge.holes == (anchor_t.size < ANCHOR_T.size)
