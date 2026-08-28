"""Mapping ticks onto a parent clock, and refusing where the mapping is undefined."""

import numpy as np
import pytest

from nwb_lake_writer.align import Unanchored, align, rate

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
    global fit does not. A jittered final anchor must not steer the extrapolation."""
    jittered = ANCHOR_P.copy()
    jittered[-1] += 400  # one bad edge detection
    beyond = np.array([ANCHOR_T[-1] + AP // 2], dtype=np.int64)
    parent, defined = align(beyond, ANCHOR_T, jittered)
    assert defined.all()
    segment = jittered[-1] + (jittered[-1] - jittered[-2]) // 2
    assert abs(int(parent[0]) - segment) > 100  # not the terminal segment's answer


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
