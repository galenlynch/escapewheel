"""R39's time origin, and the measured bound Part 01 §3.9 requires to reach it.

Both are arithmetic over anchors rather than adapter behaviour, so they are exercised
directly: an origin that is wrong by a tick is invisible in a packet and shifts every second
a consumer derives from it.
"""

import numpy as np
import pytest

from escapewheel_writer.notes import NoteCode, coded
from escapewheel_writer.session import (
    TOLERANCE,
    Context,
    _bound_for,
    _declare_withheld,
    _time_origin,
)

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


def test_the_far_end_of_the_window_counts_too():
    """A sync train that stops well before the recording does needs the bound at that end,
    and only the window says so -- the anchors themselves cannot."""
    late = int(TICKS[-1]) + 3 * AP
    bound, measured = _bound_for(BY_CLOCK, {"probe": (int(TICKS[0]), late)}, TOLERANCE, HARP)
    assert measured["distance"] == 3
    assert bound == 3.0


def test_data_inside_one_interval_needs_no_measurement():
    """A packet that says nothing about its bound is unchanged by R37 (§3.3)."""
    bound, measured = _bound_for(BY_CLOCK, {"probe": (FIRST - AP + 1, int(TICKS[-1]))}, TOLERANCE, HARP)
    assert (bound, measured) == (1.0, {})


def test_reaching_further_is_measured_and_recorded():
    bound, measured = _bound_for(BY_CLOCK, {"probe": (0, int(TICKS[-1]))}, TOLERANCE, HARP)
    assert bound == 2.0
    assert measured["distance"] == 2
    assert measured["used"] == 2.0
    assert measured["per_clock"]["probe"]["n"] == TICKS.size - 2
    # Part 01 §3.9: all three, so a reader may apply a stricter rule than the writer did.
    assert {"median_error_seconds", "p95_error_seconds", "max_error_seconds"} <= set(measured)


def test_the_gate_is_the_95th_percentile_not_the_median():
    """Part 01 §3.9: a bound is a statement about what a consumer may rely on."""
    tail = PARENTS.copy()
    tail[::7] += 900  # a seventh of the anchors badly placed; the median never sees them
    _, measured = _bound_for({"probe": (TICKS, tail)}, {"probe": (0, int(TICKS[-1]))}, TOLERANCE, HARP)
    assert measured["median_error_seconds"] < TOLERANCE < measured["p95_error_seconds"]
    assert measured["used"] == 1.0


def test_a_clock_that_cannot_meet_the_tolerance_keeps_the_default():
    """The measurement is allowed to refuse: a bound is earned, not declared."""
    wandering = PARENTS + np.rint(400 * np.sin(np.arange(TICKS.size))).astype(np.int64)
    bound, measured = _bound_for({"probe": (TICKS, wandering)}, {"probe": (0, int(TICKS[-1]))}, 1e-5, HARP)
    assert bound == 1.0
    assert measured["used"] == 1.0
    assert measured["p95_error_seconds"] > 1e-5


def test_three_milliseconds_admits_what_this_rig_actually_needs():
    """Part 01 §3.9: the default is set above the estimator's measured p95, not at its median."""
    bound, measured = _bound_for(BY_CLOCK, {"probe": (0, int(TICKS[-1]))}, TOLERANCE, HARP)
    assert bound == 2.0
    assert measured["p95_error_seconds"] < TOLERANCE / 10


# -- the origin ------------------------------------------------------------------------


def test_the_origin_is_the_earliest_start_across_every_clock():
    """Part 01 §2.2: no modality is preferred, so the earliest wins wherever it came from."""
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
    """Part 01 §2.2: a minimum over some of the clocks is not the minimum, so nothing is stated."""
    intervals = [{"clock_id": "probe", "start_tick": 0}]
    assert _time_origin(context_on(), intervals, BY_CLOCK, bound=1.0) is None


def test_a_clock_with_no_anchors_yields_no_origin():
    intervals = [{"clock_id": "elsewhere", "start_tick": 0}]
    assert _time_origin(context_on(), intervals, BY_CLOCK, bound=2.0) is None


# -- R99 §3.2: the terminal-anchor test reaches the clock rows the sorter staged ------------


class _Sync:
    def __init__(self, withheld):
        self.withheld = withheld


class _Staged:
    """A writer stub recording what `stamp` was asked to set."""

    def __init__(self, reach=None):
        self.calls = []
        self._reach = reach

    def stamp(self, resource_id, match, values):
        self.calls.append((resource_id, match, values))
        return len(values) if self._reach is None else self._reach


def _context(withheld):
    context = Context.__new__(Context)
    context.sources = {"sync": _Sync(withheld)}
    context.notes = []
    return context


def test_a_clock_the_test_kept_records_false_not_nothing():
    """Part 02 §12.6: a silent absence and a recorded zero are different facts."""
    writer = _Staged()
    _declare_withheld(_context({"probeA": {"anchors": [], "n_withheld": 0}}), writer, lambda _: None)
    (resource, match, values) = writer.calls[0]
    assert (resource, match) == ("core.clocks", "clock_id")
    assert values["probeA"] == {"withheld_first_anchor": False, "withheld_last_anchor": False}


def test_which_terminal_went_is_what_the_two_columns_say():
    writer = _Staged()
    _declare_withheld(_context({"probeA": {"anchors": ["first"], "n_withheld": 1}}), writer, lambda _: None)
    assert writer.calls[0][2]["probeA"] == {"withheld_first_anchor": True, "withheld_last_anchor": False}


def test_a_clock_the_test_never_reached_is_not_stamped_at_all():
    """Null is the third state, so a clock absent from the map keeps both columns null."""
    writer = _Staged()
    _declare_withheld(_context({}), writer, lambda _: None)
    assert writer.calls == []


def test_a_clock_the_stamp_could_not_reach_is_noted():
    """A silent miss would leave the packet saying the test never ran on that clock."""
    context = _context({"probeA": {"anchors": [], "n_withheld": 0}, "probeB": {"anchors": ["last"], "n_withheld": 1}})
    _declare_withheld(context, _Staged(reach=1), lambda _: None)
    (partial,) = coded(context.notes, NoteCode.ANCHOR_TEST_PARTIAL)
    assert "2 clocks and 1 of them" in partial
