"""Map ticks from one clock onto its parent, through anchors.

Lives in the reader because both reading and writing need it and there must be one of it: a
packet whose spikes are mapped at write time and a caller mapping the same spikes at read
time have to agree, and two implementations of a piecewise map agree only by luck.

This is R13 §3's piecewise-linear mapping with R27 §5.3's bound, and it is the only place
that arithmetic is written. A spike's tick is exact on its probe's clock and means nothing
beside another probe's; the anchors are what relate them, and this turns the relation into
numbers.

Three rules, and the second is the one that was wrong
-----------------------------------------------------

Let *m* be the median interval between a clock's anchors.

1. Between two anchors no more than 2*m* apart, linear interpolation on that pair.
2. Beyond the terminal anchors, ``parent(a) + rate * (t - a)`` where *a* is the nearer
   terminal anchor and `rate` is fitted over the whole sequence (R37 §3.1). Both halves
   matter and for different reasons. The *rate* is global because a terminal segment's slope
   comes from two anchors and degrades to ~0.9 ms; the *offset* is the terminal anchor's own
   parent tick because a global fit's intercept carries the session's clock wander -- ±1.7 ms
   over 6,387 s here, which a straight line cannot bend to follow. Anchoring at the terminal
   anchor drops p95 extrapolation error from 525 µs to 258 µs (R37 §2).
3. Anywhere further than *m* from every anchor -- past the ends, or inside a wider gap -- the
   mapping is undefined by default, and this returns a mask saying so rather than a plausible
   number. R37 §3.3 makes the real bound one on *error*: a caller that has measured its own
   clocks may widen `bound`, and one that has not gets R27 §5.3's distance unchanged.

The mask is not a formality. On a real session the first sync pulse arrives 18,000 to 28,000
samples after the recording starts, so the spikes in that window have no defined parent tick
and are exactly the ones a caller would otherwise silently misplace.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray

from .dictionaries import values, where

#: How far from an anchor the mapping stays defined, as a multiple of the median anchor
#: interval (R27 §5.3). One, so that the same threshold covers a gap between anchors and the
#: unanchored ends -- the bound and the region it has to cover are the same quantity, because
#: a free-running sync pulse leaves less than one interval at each end by construction.
BOUND = 1.0


class Unanchored(ValueError):
    """A clock has too few anchors to define a mapping.

    Two anchors define a segment but no median interval worth trusting, so the bound would
    rest on a single observation.
    """


def rate(anchor_t: NDArray[np.int64], anchor_p: NDArray[np.int64]) -> tuple[float, float]:
    """Fit parent ticks against ticks over the whole anchor sequence.

    Returns slope and intercept. Centred before fitting: anchors run to 5.5e11 on a HARP
    clock, and a least-squares fit on raw values there loses precision that the residual
    cannot afford.
    """
    centre_t = float(anchor_t.mean())
    centre_p = float(anchor_p.mean())
    dt = anchor_t.astype(np.float64) - centre_t
    dp = anchor_p.astype(np.float64) - centre_p
    slope = float(dt @ dp / (dt @ dt))
    return slope, centre_p - slope * centre_t


def align(
    ticks: NDArray[np.int64],
    anchor_t: NDArray[np.int64],
    anchor_p: NDArray[np.int64],
    *,
    bound: float = BOUND,
) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
    """Map ticks onto the parent clock.

    Parameters
    ----------
    ticks : numpy.ndarray of int64
        Ticks on the child clock, in any order.
    anchor_t, anchor_p : numpy.ndarray of int64
        The anchor pairs, both strictly increasing (R13 §3).
    bound : float, default `BOUND`
        How far from an anchor the mapping stays defined, in median anchor intervals.

    Returns
    -------
    parent : numpy.ndarray of int64
        The parent tick for each input. Meaningless where `defined` is False.
    defined : numpy.ndarray of bool
        Whether the mapping is defined there. A caller writes null where it is not.

    Raises
    ------
    Unanchored
        If fewer than three anchors are given.
    ValueError
        If either sequence does not strictly increase, since interpolation between them
        would then be undefined (R13 §3).
    """
    anchor_t = np.asarray(anchor_t, dtype=np.int64)
    anchor_p = np.asarray(anchor_p, dtype=np.int64)
    if anchor_t.size < 3:
        raise Unanchored(f"{anchor_t.size} anchors define no median interval to bound by")
    if not ((np.diff(anchor_t) > 0).all() and (np.diff(anchor_p) > 0).all()):
        raise ValueError("anchors do not increase together, so interpolation between them is undefined")

    ticks = np.asarray(ticks, dtype=np.int64)
    span = float(np.median(np.diff(anchor_t))) * bound

    # Interior: np.interp is a single C pass doing the search and the lerp together, and is an
    # order of magnitude faster than gathering the bracketing pairs and computing them here.
    parent = np.rint(np.interp(ticks, anchor_t, anchor_p)).astype(np.int64)

    # Outside the anchor span np.interp clamps to the terminal value, which is a wrong answer
    # rather than a missing one, so both ends are recomputed. R37 §3.1: the globally fitted
    # rate, applied from the terminal anchor's own parent tick. The fit's intercept is not
    # used -- it is the one place a line has to represent the whole session's wander at once,
    # and it misses local truth by an amount that does not shrink with distance.
    slope, _ = rate(anchor_t, anchor_p)
    for end, tick, parent_tick in (
        (ticks < anchor_t[0], anchor_t[0], anchor_p[0]),
        (ticks > anchor_t[-1], anchor_t[-1], anchor_p[-1]),
    ):
        if end.any():
            offsets = (ticks[end] - tick).astype(np.float64)
            parent[end] = parent_tick + np.rint(slope * offsets).astype(np.int64)

    # Distance to the nearest anchor, which is what the bound is on -- the same threshold for
    # a gap between anchors and for the unanchored ends.
    left = np.searchsorted(anchor_t, ticks, side="right") - 1
    np.clip(left, 0, anchor_t.size - 1, out=left)
    right = np.minimum(left + 1, anchor_t.size - 1)
    nearest = np.minimum(np.abs(ticks - anchor_t[left]), np.abs(anchor_t[right] - ticks))
    return parent, nearest <= span


def extrapolation_error(
    anchor_t: NDArray[np.int64],
    anchor_p: NDArray[np.int64],
    distance: float,
) -> dict[str, float]:
    """Measure :func:`align`'s out-of-range estimator at a given distance, in parent ticks.

    R37 §3.3 makes the bound one on error rather than on distance, and requires a writer that
    wants more than R27 §5.3's one median interval to *measure* it at the distance it intends
    to use. This is that measurement: every interior anchor stands in for a terminal one, the
    §3.1 estimator predicts the anchor `distance` median intervals further on, and the spread
    of the residuals is what the tolerance is compared against.

    Interior positions are used because a terminal anchor is the one place the answer cannot
    be checked -- there is nothing beyond it to compare against -- and because a clock's
    interior is where its wander is representative rather than exceptional.

    Parameters
    ----------
    anchor_t, anchor_p : numpy.ndarray of int64
        The anchor pairs, strictly increasing.
    distance : float
        How far beyond the terminal anchor to predict, in median anchor intervals.

    Returns
    -------
    dict
        `median`, `p95` and `max` absolute error in parent ticks, and the `n` predictions
        they were taken over. Empty where the clock has too few anchors to measure at all.
    """
    anchor_t = np.asarray(anchor_t, dtype=np.int64)
    anchor_p = np.asarray(anchor_p, dtype=np.int64)
    step = round(distance) or 1
    if anchor_t.size < step + 3:
        return {}
    slope, _ = rate(anchor_t, anchor_p)
    frm = np.arange(anchor_t.size - step)
    predicted = anchor_p[frm] + slope * (anchor_t[frm + step] - anchor_t[frm]).astype(np.float64)
    error = np.abs(anchor_p[frm + step].astype(np.float64) - predicted)
    return {
        "median": float(np.median(error)),
        "p95": float(np.percentile(error, 95)),
        "max": float(error.max()),
        "n": int(error.size),
    }


class NotAligned(ValueError):
    """A clock the spikes are on has no anchors, so its ticks reach no reference."""


def anchors(packet: Any) -> dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]]:
    """Read `core.clock_anchors` into arrays per clock."""
    table = packet.table("core.clock_anchors")
    clock = table.column("clock_id").to_pylist()
    tick = np.asarray(table.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    parent = np.asarray(table.column("parent_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    out: dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]] = {}
    for name in dict.fromkeys(clock):
        where = np.array([i for i, c in enumerate(clock) if c == name])
        order = np.argsort(tick[where], kind="stable")
        out[name] = (tick[where][order], parent[where][order])
    return out


def declared_bound(packet: Any) -> float:
    """Return the alignment bound the packet's writer established, or `BOUND`.

    R37 §3.3 lets a writer map further than one median anchor interval once it has *measured*
    the estimator at the distance it intends to use, and R37 §4 puts that record in
    `core.processing_runs.parameters` rather than adding a column. So this is where the number
    lives, and reading it is what makes a consumer's mapping match the writer's: a packet whose
    spikes were placed at a bound of two and whose reader maps at one disagrees with itself
    about which of its own rows have a time.

    The largest bound any run measured wins, since a run that widened the bound is the one that
    wrote the ticks in question. A packet with no such record maps at `BOUND`, which is what
    R37 §3.3 says a packet that says nothing means.
    """
    import json

    try:
        runs = packet.table("core.processing_runs", columns=["parameters"])
    except Exception:  # noqa: BLE001 -- an absent or unreadable table is simply no record
        return BOUND
    found = [BOUND]
    for raw in runs.column("parameters").to_pylist():
        if not raw:
            continue
        try:
            measured = json.loads(raw).get("alignment_bound") or {}
        except (TypeError, ValueError):
            continue
        if isinstance(measured, dict) and isinstance(measured.get("used"), int | float):
            found.append(float(measured["used"]))
    return max(found)


def reference_clock(packet: Any) -> str:
    """Return the clock a session reports its times on (R27 §2)."""
    sessions = packet.table("core.sessions")
    declared = (
        sessions.column("reference_clock_id").to_pylist() if "reference_clock_id" in sessions.column_names else []
    )
    if named := [d for d in declared if d]:
        return str(named[0])
    raise NotAligned("the session declares no reference_clock_id (R27 §2), so there is nothing to map onto")


def mapped(batch: pa.RecordBatch, reference: str, anchors: Any, bound: float) -> tuple[Any, Any]:
    """Map one batch's ticks onto the reference clock, returning the ticks and what to keep."""
    ticks = np.asarray(batch.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    clocks = batch.column("clock_id")
    parent = np.empty(ticks.size, dtype=np.int64)
    keep = np.zeros(ticks.size, dtype=bool)
    # A batch spans at most two streams, since the table is sorted by sorting_run_id and each
    # stream is one run, so this loop runs once or twice. Its *body* must still stay in Arrow:
    # asking for the column as Python strings to group it costs a string object per spike, and
    # the comparison that follows is over a handful of distinct values either way.
    for name in values(clocks):
        rows = where(clocks, name)
        if not rows.size:
            continue
        if name == reference:
            parent[rows], keep[rows] = ticks[rows], True
            continue
        if name not in anchors:
            raise NotAligned(f"{name} carries no anchors, so its ticks reach no reference clock")
        parent[rows], keep[rows] = align(ticks[rows], *anchors[name], bound=bound)
    return parent, keep


def stored_span(
    by_clock: dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]],
    target: str,
    span: tuple[int, int],
) -> tuple[int, int]:
    """Widen a range on `target` into one that covers it on every stored clock.

    A constraint a caller states on the reference clock has to reach the file as a constraint
    on the ticks the file holds, and each clock maps differently, so the pushed range is the
    union over clocks. It is deliberately loose: its only job is to let row groups that cannot
    match go unread, and the exact range is applied after mapping, where every row is on one
    clock and the comparison means something.
    """
    lo, hi = span
    lows, highs = [lo], [hi]
    for anchor_t, anchor_p in by_clock.values():
        if anchor_t.size < 2:
            continue
        # The inverse of the same piecewise map: the anchor pairs, read the other way.
        ends = np.interp([lo, hi], anchor_p, anchor_t)
        # One anchor interval of slack each way, which is the bound the forward map allows.
        slack = float(np.median(np.diff(anchor_t)))
        lows.append(int(np.floor(ends[0] - slack)))
        highs.append(int(np.ceil(ends[1] + slack)))
    return min(lows), max(highs)


__all__ = [
    "BOUND",
    "NotAligned",
    "Unanchored",
    "align",
    "anchors",
    "declared_bound",
    "extrapolation_error",
    "mapped",
    "rate",
    "reference_clock",
    "stored_span",
]
