"""Mapping ticks onto a parent clock, and refusing where the mapping is undefined."""

import json

import numpy as np
import pyarrow as pa
import pytest

from escapewheel_reader import open_packet
from escapewheel_reader.clocks import BOUND, Unanchored, align, declared_bound, extrapolation_error, rate

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
    """R27 §5.3 applies one threshold both ways: a hole between anchors is the same
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
    """R27 §5.2: the terminal segment's slope comes from two anchors and degrades; the
    global fit does not. A jittered final anchor must not steer the *rate*."""
    jittered = ANCHOR_P.copy()
    jittered[-1] += 400  # one bad edge detection
    beyond = np.array([ANCHOR_T[-1] + AP // 2], dtype=np.int64)
    parent, defined = align(beyond, ANCHOR_T, jittered)
    assert defined.all()
    segment = jittered[-1] + (jittered[-1] - jittered[-2]) // 2
    assert abs(int(parent[0]) - segment) > 100  # not the terminal segment's answer


def test_extrapolation_starts_at_the_terminal_anchor():
    """R37 §3.1: the offset is the terminal anchor's parent tick, not a global intercept.

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
    """The finding R37 was written for: a clock that wanders leaves a fitted line offset
    from local truth at the ends, and the offset does not shrink with distance."""
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


# -- measuring the bound (R37 §3.3) ----------------------------------------------------


def test_a_clean_clock_extrapolates_within_quantization():
    """The estimator on a straight sequence costs rounding and nothing else."""
    measured = extrapolation_error(ANCHOR_T, ANCHOR_P, 1)
    assert measured["n"] == ANCHOR_T.size - 1
    assert measured["max"] <= 1


def test_error_grows_with_the_bend_not_with_the_distance():
    """R37 §2's finding: what costs is the sequence's wander, not how far you reach."""
    wandering = ANCHOR_P + np.rint(300 * np.sin(np.arange(ANCHOR_T.size) * 0.9)).astype(np.int64)
    assert extrapolation_error(ANCHOR_T, wandering, 1)["median"] > extrapolation_error(ANCHOR_T, ANCHOR_P, 1)["median"]


def test_too_few_anchors_measure_nothing():
    assert extrapolation_error(ANCHOR_T[:3], ANCHOR_P[:3], 5) == {}


# -- reading the bound a writer established (R37 §4) ------------------------------------


class _Runs:
    """A packet stub carrying only what `declared_bound` reads."""

    def __init__(self, *parameters):
        self._table = pa.table({"parameters": pa.array(parameters, pa.string())})

    def table(self, resource_id, columns=None):
        del resource_id, columns
        return self._table


def test_a_packet_that_says_nothing_maps_at_the_default():
    assert declared_bound(_Runs(json.dumps({"recipe": {}}))) == BOUND


def test_the_measured_bound_is_read_from_the_run_that_measured_it():
    """R37 §4 puts it in `parameters` rather than in a column, so this is where it lives."""
    assert declared_bound(_Runs(json.dumps({"alignment_bound": {"used": 2.0, "distance": 2}}))) == 2.0


def test_the_widest_measured_bound_wins():
    runs = _Runs(json.dumps({"alignment_bound": {"used": 3.0}}), json.dumps({"bound": 1.0}), None)
    assert declared_bound(runs) == 3.0


def test_an_unreadable_record_is_no_record():
    """Free-form JSON someone else wrote must not be able to break a read path."""
    assert declared_bound(_Runs("not json", json.dumps({"alignment_bound": "nonsense"}))) == BOUND


# -- the free function is the implementation; the method is a delegate --------------------


def test_on_clock_is_the_same_whether_called_as_a_function_or_a_method(two_clock_packet):
    """The delegate exists for discoverability and must not acquire behaviour of its own."""
    from escapewheel_reader.clocks import on_clock

    packet = open_packet(two_clock_packet)
    spikes = packet.table("core.spike_events")
    assert on_clock(packet, spikes).to_pylist() == packet.on_clock(spikes).to_pylist()


def test_seconds_is_the_same_whether_called_as_a_function_or_a_method(two_clock_packet):
    """As above. Two surfaces over one implementation, never two implementations."""
    from escapewheel_reader.clocks import on_clock, seconds

    packet = open_packet(two_clock_packet)
    mapped_spikes = on_clock(packet, packet.table("core.spike_events"))
    assert seconds(packet, mapped_spikes).to_pylist() == packet.seconds(mapped_spikes).to_pylist()


def test_the_packet_carries_no_transformation_of_its_own(two_clock_packet):
    """`Packet` is manifest, resolution, IO and registration. Anything that could be a free
    function is one, so the delegates are one line each and there are few of them."""
    import inspect

    from escapewheel_reader.packet import Packet

    for name in ("on_clock", "seconds"):
        body = [
            line
            for line in inspect.getsource(getattr(Packet, name)).splitlines()
            if line.strip() and not line.strip().startswith(('"""', "#", "def ", "Delegates"))
        ]
        assert any(line.strip().startswith("return ") for line in body), name
