"""R39's time origin, and the measured bound R37 §3.3 requires to reach it.

Both are arithmetic over anchors rather than adapter behaviour, so they are exercised
directly: an origin that is wrong by a tick is invisible in a packet and shifts every second
a consumer derives from it.
"""

import numpy as np
import pytest

from nwb_lake_writer.session import TOLERANCE, Context, _bound_for, _time_origin

AP, HARP = 30000, 31250

#: Sixty anchors a second apart, and a probe clock whose tick 0 falls a second before the
#: first of them -- which is what withholding a displaced first anchor leaves (R37 §1).
FIRST = 2 * AP
TICKS = FIRST + np.arange(60, dtype=np.int64) * AP
PARENTS = np.rint(TICKS * (HARP / AP)).astype(np.int64) + 553_191_712_312
BY_CLOCK = {"probe": (TICKS, PARENTS)}


def context_on(reference="harp"):
    context = Context(session_id="s")
    context.reference = type("Clock", (), {"clock_id": reference})()
    return context


# -- choosing the bound ----------------------------------------------------------------


def test_data_inside_one_interval_needs_no_measurement():
    """A packet that says nothing about its bound is unchanged by R37 (§3.3)."""
    bound, measured = _bound_for(BY_CLOCK, {"probe": FIRST - AP + 1}, TOLERANCE)
    assert (bound, measured) == (1.0, {})


def test_reaching_further_is_measured_and_recorded():
    bound, measured = _bound_for(BY_CLOCK, {"probe": 0}, TOLERANCE)
    assert bound == 2.0
    assert measured["distance"] == 2
    assert measured["used"] == 2.0
    assert measured["per_clock"]["probe"]["n"] == TICKS.size - 2


def test_a_clock_that_cannot_meet_the_tolerance_keeps_the_default():
    """The measurement is allowed to refuse: a bound is earned, not declared."""
    wandering = PARENTS + np.rint(400 * np.sin(np.arange(TICKS.size))).astype(np.int64)
    bound, measured = _bound_for({"probe": (TICKS, wandering)}, {"probe": 0}, TOLERANCE)
    assert bound == 1.0
    assert measured["used"] == 1.0
    assert measured["median_error"] > TOLERANCE


# -- the origin ------------------------------------------------------------------------


def test_the_origin_is_the_earliest_start_across_every_clock():
    """R39 §2.1: no modality is preferred, so the earliest wins wherever it came from."""
    intervals = [
        {"clock_id": "probe", "start_tick": 0},
        {"clock_id": "harp", "start_tick": int(PARENTS[0])},
    ]
    origin = _time_origin(context_on(), intervals, BY_CLOCK, bound=2.0)
    assert origin == pytest.approx(PARENTS[0] - round(FIRST * HARP / AP), abs=1)
    assert origin < PARENTS[0]


def test_a_reference_clock_window_is_taken_as_it_stands():
    intervals = [{"clock_id": "harp", "start_tick": 12345}]
    assert _time_origin(context_on(), intervals, BY_CLOCK, bound=1.0) == 12345


def test_an_unmappable_window_yields_no_origin():
    """R39 §2.4: a minimum over some of the clocks is not the minimum, so nothing is stated."""
    intervals = [{"clock_id": "probe", "start_tick": 0}]
    assert _time_origin(context_on(), intervals, BY_CLOCK, bound=1.0) is None


def test_a_clock_with_no_anchors_yields_no_origin():
    intervals = [{"clock_id": "elsewhere", "start_tick": 0}]
    assert _time_origin(context_on(), intervals, BY_CLOCK, bound=2.0) is None
