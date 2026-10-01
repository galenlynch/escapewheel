"""The checks a clock's anchors are put to, as functions of the anchor arrays alone.

- :func:`suspect_terminals` -- the test of a clock's first and last anchor.
- :func:`phase_discontinuities` -- the places where the parent clock advances by more or less
  than a clock's own rate predicts.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

#: How many neighbours a terminal anchor is predicted from in `suspect_terminals`, and how many
#: interior anchors the same prediction is repeated at to get the distribution it is judged
#: against. Thirty neighbours is what R37 §3.1 measured a local rate over; six hundred
#: positions is enough for a stable 99th percentile and costs a millisecond.
NEIGHBOURS, INTERIOR = 30, 600

#: A phase discontinuity in the reference alignment larger than this is reported, in seconds.
#:
#: 400 µs sits between how far an undisturbed anchor interval's parent advance departs from the
#: clock's own median ratio and what a known upstream discontinuity costs, with about twice the
#: margin either way. It is well below Part 01 §3.9's 3 ms alignment tolerance, so a packet can carry a
#: reported discontinuity and still align within bound -- reporting is not refusing.
DISCONTINUITY = 4e-4

#: Which percentile of a clock's own interior residuals a terminal anchor must stay inside.
#: Stated on the clock's spread rather than as a fixed tolerance because anchor quality is a
#: property of a rig and a session, not of the format.
SUSPECT_PERCENTILE = 99.0


def phase_discontinuities(
    ticks: NDArray[np.int64], parents: NDArray[np.int64], rate: float, limit: float = DISCONTINUITY
) -> list[dict[str, Any]]:
    """Find places where the parent clock's phase steps against this clock's own rate.

    An anchor interval should advance the parent by the interval's own length times the clock
    ratio. Where it does not, the parent's phase moved -- and because a clock's map is exact at
    every anchor, the map faithfully carries that step rather than smoothing it away. Nothing
    downstream can see it, so the writer says so.

    Consecutive offending intervals are one event: a step arrives as a ramp over the two
    intervals either side of a discarded upstream anchor rather than as a jump.

    Parameters
    ----------
    ticks, parents : numpy.ndarray of int64
        The anchor pairs, strictly increasing.
    rate : float
        The parent clock's rate in hertz, to report sizes as durations.
    limit : float
        The smallest discontinuity worth reporting, in seconds.

    Returns
    -------
    list of dict
        One entry per event: where it is on both clocks, and how far the parent moved.
    """
    if ticks.size < 3:
        return []
    step, parent_step = np.diff(ticks).astype(np.float64), np.diff(parents).astype(np.float64)
    ratio = float(np.median(parent_step / step))
    residual = parent_step - step * ratio
    offending = np.flatnonzero(np.abs(residual) > limit * rate)
    if not offending.size:
        return []
    events = np.split(offending, np.flatnonzero(np.diff(offending) > 1) + 1)
    return [
        {
            "t_tick": int(ticks[group[0]]),
            "parent_tick": int(parents[group[0]]),
            "seconds": round(float(residual[group].sum()) / rate, 9),
            "anchor_intervals": int(group.size),
        }
        for group in events
    ]


def _predict(at: int, ticks: NDArray[np.int64], parents: NDArray[np.int64], frm: int) -> float:
    """Predict a parent tick by the test's estimator: the fitted rate, applied from the anchor at index `frm`."""
    centre_t, centre_p = float(ticks.mean()), float(parents.mean())
    dt = ticks.astype(np.float64) - centre_t
    slope = float(dt @ (parents.astype(np.float64) - centre_p) / (dt @ dt))
    return float(parents[frm]) + slope * float(at - ticks[frm])


def suspect_terminals(
    ticks: NDArray[np.int64],
    parents: NDArray[np.int64],
    *,
    neighbours: int = NEIGHBOURS,
    interior: int = INTERIOR,
) -> tuple[bool, bool, dict[str, float]]:
    """Apply R37 §3.2's test to a clock's first and last anchor.

    Each terminal anchor is predicted from the `neighbours` anchors on its inward side and
    the residual compared against the same one-sided residual taken at `interior` interior
    positions. A terminal anchor outside that distribution's 99th percentile is one the
    writer has reason to believe is misplaced, and such an anchor is withheld (Part 02 §12.6).

    The interior positions are the control that makes the test mean anything: they run the
    identical estimator where nothing is suspected, so a large residual at the end is
    attributable to the anchor rather than to the estimator being poorly conditioned there.

    Returns
    -------
    tuple
        Whether to drop the first anchor, whether to drop the last, and the residuals in
        parent ticks -- `first`, `last` and the `threshold` they were judged against.
    """
    room = neighbours + 2
    if ticks.size < room + 2:
        return False, False, {}
    control = np.abs(
        [
            _predict(ticks[i], ticks[i + 1 : i + 1 + neighbours], parents[i + 1 : i + 1 + neighbours], 0) - parents[i]
            for i in range(1, min(interior, ticks.size - room))
        ]
    )
    threshold = float(np.percentile(control, SUSPECT_PERCENTILE))
    first = float(parents[0] - _predict(ticks[0], ticks[1 : 1 + neighbours], parents[1 : 1 + neighbours], 0))
    last = float(parents[-1] - _predict(ticks[-1], ticks[-1 - neighbours : -1], parents[-1 - neighbours : -1], -1))
    return (
        abs(first) > threshold,
        abs(last) > threshold,
        {"first": round(first, 1), "last": round(last, 1), "threshold": round(threshold, 1)},
    )


__all__ = [
    "phase_discontinuities",
    "suspect_terminals",
]
