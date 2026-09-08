"""A clock quantizes or refuses; it never fits."""

from datetime import datetime, timezone

import numpy as np
import pytest

from escapewheel_writer import Clock, NonFinite, OffGrid
from escapewheel_writer.clock import HARP_TICK_RATE_HZ


def harp(**kwargs):
    return Clock("harp", session_id="s1", name="HARP", tick_rate_num=HARP_TICK_RATE_HZ, origin="HARP epoch", **kwargs)


def test_seconds_on_the_grid_quantize_exactly():
    assert harp().ticks([1.0, 0.000032, 0.0]).tolist() == [31250, 1, 0]


def test_ticks_round_trip_at_the_harp_epoch():
    """The magnitude that matters: 1.16e7 s, where float64 retains only 1.86 ns."""
    seconds = np.array([11576039.861504, 11576047.063488, 11583848.0])
    assert np.array_equal(harp().ticks(seconds) / HARP_TICK_RATE_HZ, seconds)


def test_off_grid_seconds_are_refused():
    with pytest.raises(OffGrid) as caught:
        harp().ticks([1.0, 1.0000005])
    assert caught.value.n_off == 1
    assert "fitting a rate" in str(caught.value)


def test_a_wrong_rate_is_refused_rather_than_silently_rescaling():
    """The grid check is what makes passing the wrong clock loud instead of plausible."""
    on_harp = [0.000032, 0.000064, 0.000096]
    assert harp().ticks(on_harp).tolist() == [1, 2, 3]
    with pytest.raises(OffGrid):
        Clock("c", session_id="s1", name="c", tick_rate_num=30000, origin="e").ticks(on_harp)


def test_non_finite_is_refused():
    with pytest.raises(NonFinite, match="1 of 3"):
        harp().ticks([1.0, np.nan, 2.0])


def test_an_empty_input_is_empty_not_an_error():
    assert harp().ticks([]).tolist() == []


def test_a_non_positive_rate_is_rejected_at_construction():
    with pytest.raises(ValueError, match="not positive"):
        Clock("c", session_id="s1", name="c", tick_rate_num=0, origin="e")


def test_the_record_carries_one_rate_form():
    """R95 §3.2. Both forms made the float a copy of `tick_rate_num`, free to disagree."""
    row = harp().record()
    assert (row["tick_rate_num"], row["tick_rate_den"]) == (31250, 1)
    assert "tick_rate_hz" not in row
    assert "tick_zero_utc" not in row  # absent unless the source recorded it


def test_tick_zero_is_written_only_when_given():
    epoch = datetime(2024, 11, 27, 0, 51, 12, tzinfo=timezone.utc)
    assert harp(tick_zero_utc=epoch).record()["tick_zero_utc"] == epoch


def test_a_rational_rate_is_not_the_same_grid_as_its_float():
    """30000/1.0001 Hz and 30000 Hz agree at tick 0 and nowhere useful after it."""
    drifting = Clock("c", session_id="s1", name="c", tick_rate_num=300000000, tick_rate_den=10001, origin="e")
    assert drifting.ticks([10001 / 300000000]).tolist() == [1]
    with pytest.raises(OffGrid):
        drifting.ticks([1 / 30000])


def test_epoch_from_does_its_arithmetic_in_utc():
    """Aware-datetime subtraction is wall-clock arithmetic, and this crosses a DST boundary.

    The session is PDT; tick 0 is 134 days earlier, in PST. Subtracting the elapsed time from
    the local wall clock and re-resolving the offset lands an hour late, silently.
    """
    from zoneinfo import ZoneInfo

    from escapewheel_writer.clock import epoch_from

    session = datetime(2025, 4, 9, 17, 25, 12, tzinfo=ZoneInfo("America/Los_Angeles"))
    epoch = epoch_from(session, 361751245672, HARP_TICK_RATE_HZ)
    assert epoch == datetime(2024, 11, 27, 0, 51, 12, 138496, tzinfo=timezone.utc)
    # what the naive form gives, an hour out
    assert session - (session - epoch) != epoch.astimezone(ZoneInfo("America/Los_Angeles"))


def test_epoch_from_refuses_an_unlocated_instant():
    from escapewheel_writer.clock import epoch_from

    with pytest.raises(ValueError, match="does not locate"):
        epoch_from(datetime(2025, 4, 9, 17, 25, 12), 1, HARP_TICK_RATE_HZ)  # noqa: DTZ001 -- the point
