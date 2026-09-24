"""Map ticks from one clock onto its parent, through anchors.

Lives in the reader because both reading and writing need it and there must be one of it: a
packet whose spikes are mapped at write time and a caller mapping the same spikes at read
time have to agree, and two implementations of a piecewise map agree only by luck.

This is R13 §3's piecewise-linear mapping with Part 01 §3.9's bound, and it is the only place
that arithmetic is written. A spike's tick is exact on its probe's clock and means nothing
beside another probe's; the anchors are what relate them, and this turns the relation into
numbers.

Three rules, and the second is the one that was wrong
-----------------------------------------------------

Let *m* be the median interval between a clock's anchors.

1. Between two anchors no more than 2*m* apart, linear interpolation on that pair.
2. Beyond the terminal anchors, ``parent(a) + rate * (t - a)`` where *a* is the nearer
   terminal anchor and `rate` is fitted over the whole sequence (Part 01 §3.9). Both halves
   matter and for different reasons. The *rate* is global because a terminal segment's slope
   comes from two anchors and degrades to ~0.9 ms; the *offset* is the terminal anchor's own
   parent tick because a global fit's intercept carries the session's clock wander -- ±1.7 ms
   over 6,387 s here, which a straight line cannot bend to follow. Anchoring at the terminal
   anchor drops p95 extrapolation error from 525 µs to 258 µs (R37 §2).
3. Anywhere further than *m* from every anchor -- past the ends, or inside a wider gap -- the
   mapping is undefined by default, and this returns a mask saying so rather than a plausible
   number. Part 01 §3.9 makes the real bound one on *error*: a caller that has measured its own
   clocks may widen `bound`, and one that has not gets Part 01 §3.9's distance unchanged.

The mask is not a formality. On a real session the first sync pulse arrives 18,000 to 28,000
samples after the recording starts, so the spikes in that window have no defined parent tick
and are exactly the ones a caller would otherwise silently misplace.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from numpy.typing import NDArray

from .dictionaries import values, where
from .errors import NoTimeOrigin

#: How far from an anchor the mapping stays defined, as a multiple of the median anchor
#: interval (Part 01 §3.9). One, so that the same threshold covers a gap between anchors and the
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
    # rather than a missing one, so both ends are recomputed. Part 01 §3.9: the globally fitted
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

    Part 01 §3.9 makes the bound one on error rather than on distance, and requires a writer that
    wants more than Part 01 §3.9's one median interval to *measure* it at the distance it intends
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


def anchors(packet: Any) -> dict[int, tuple[NDArray[np.int64], NDArray[np.int64]]]:
    """Read `core.clock_anchors` into arrays per clock, memoised on the packet.

    The packet owns the cache because the answer is a property of its bytes. Memoised because an
    accessor is called per unit, and reading the anchor table for each of 6,781 units would cost
    more than the spikes do.
    """
    cached = getattr(packet, "_anchor_cache", None)
    if cached is not None:
        return cached  # type: ignore[no-any-return]
    table = packet.table("core.clock_anchors")
    clock = table.column("clock_id").to_pylist()
    tick = np.asarray(table.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    parent = np.asarray(table.column("parent_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    out: dict[int, tuple[NDArray[np.int64], NDArray[np.int64]]] = {}
    for name in dict.fromkeys(clock):
        where = np.array([i for i, c in enumerate(clock) if c == name])
        order = np.argsort(tick[where], kind="stable")
        out[name] = (tick[where][order], parent[where][order])
    if hasattr(packet, "_anchor_cache"):
        packet._anchor_cache = out
    return out


def declared_bound(packet: Any) -> float:
    """Return the alignment bound the packet's writer established, or `BOUND`.

    Part 01 §3.9 lets a writer map further than one median anchor interval once it has *measured*
    the estimator at the distance it intends to use, and R99 §3.1 puts that bound in
    `core.sessions.alignment_bound`. Reading it is what makes a consumer's mapping match the
    writer's: a packet whose spikes were placed at a bound of two and whose reader maps at one
    disagrees with itself about which of its own rows have a time.

    A null column is a packet that stayed within Part 01 §3.9's default, which is `BOUND`. Where a
    packet holds several sessions the widest wins, since the reader presents them as one relation
    (R86) and a tick placed under the wider bound has to stay placed.

    Memoised on the packet, for the same reason :func:`anchors` is.
    """
    cached = getattr(packet, "_bound_cache", None)
    if cached is not None:
        return float(cached)

    try:
        sessions = packet.table("core.sessions", columns=["alignment_bound"])
    except Exception:  # noqa: BLE001 -- an absent or unreadable table is simply no record
        return BOUND
    declared = [float(v) for v in sessions.column("alignment_bound").to_pylist() if v is not None]
    widest = max([BOUND, *declared])
    if hasattr(packet, "_bound_cache"):
        packet._bound_cache = widest
    return widest


def reference_clock(packet: Any) -> int:
    """Return the clock a session reports its times on (R27 §2)."""
    sessions = packet.table("core.sessions")
    declared = (
        sessions.column("reference_clock_id").to_pylist() if "reference_clock_id" in sessions.column_names else []
    )
    if named := [d for d in declared if d is not None]:
        return int(named[0])
    raise NotAligned("the session declares no reference_clock_id (R27 §2), so there is nothing to map onto")


def mapped(batch: pa.RecordBatch, reference: Any, anchors: Any, bound: float) -> tuple[Any, Any]:
    """Map one batch's ticks onto the reference clock, returning the ticks and what to keep."""
    ticks = np.asarray(batch.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    clocks = batch.column("clock_id")
    parent = np.empty(ticks.size, dtype=np.int64)
    keep = np.zeros(ticks.size, dtype=bool)
    # A batch ordinarily spans only a few clocks because spike rows are clustered by unit and a
    # unit declares one clock. Its *body* must still stay in Arrow:
    # materialising the column as Python objects to group it costs one per spike, and the
    # comparison that follows is over a handful of distinct values either way.
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
    by_clock: dict[int, tuple[NDArray[np.int64], NDArray[np.int64]]],
    target: int,
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

# -- (packet, table) semantics ------------------------------------------------------------
#
# These take a packet and a table and return a table. They are free functions rather than
# methods because our currency is `pa.Table`, which is PyArrow's and has no `.pipe()`, so the
# method form was never available: `packet.on_clock(table)` was a method on the packet operating
# on a table, owned by neither. `Packet` keeps one-line delegates for discoverability.


def _present(column: Any) -> list[int]:
    """Distinct clock IDs in a column, read from its dictionary where it has one."""
    return sorted({int(value) for value in values(column)})


def _flat(column: Any) -> pa.Array[Any]:
    """Return one Array from a column that may arrive in chunks."""
    combined = column.combine_chunks() if isinstance(column, pa.ChunkedArray) else column
    if isinstance(combined, pa.ChunkedArray):
        return cast(
            "pa.Array[Any]",
            combined.chunk(0) if combined.num_chunks else pa.array([], type=combined.type),
        )
    return cast("pa.Array[Any]", combined)


def default_clock(packet: Any, present: list[int]) -> int:
    """Return the clock to map onto when the caller named none.

    The declared reference, or -- where a packet declares none -- the one clock the rows are
    already on, since there is then nothing to reconcile and nothing to get wrong. Rows spanning
    clocks with no reference declared are refused: that is exactly the case where returning them
    as stored invites a comparison that means nothing.
    """
    try:
        return int(packet.reference_clock())
    except NotAligned:
        if len(present) == 1:
            return present[0]
        raise


def tick_rate(packet: Any, clock_id: int) -> tuple[int, int]:
    """Return a clock's rational tick rate, which Part 01 §3.9 prefers to `tick_rate_hz`."""
    clocks = packet.table("core.clocks")
    names = clocks.column("clock_id").to_pylist()
    if clock_id not in names:
        raise NotAligned(f"core.clocks declares no {clock_id!r}, so its rate is unknown")
    row = names.index(clock_id)
    num = clocks.column("tick_rate_num")[row].as_py()
    den = clocks.column("tick_rate_den")[row].as_py() if "tick_rate_den" in clocks.column_names else 1
    if not num:
        raise NotAligned(f"{clock_id!r} declares no tick_rate_num, so seconds cannot be derived")
    return int(num), int(den or 1)


def origin(packet: Any, session_id: int | None = None) -> tuple[int, int, int]:
    """Return the session's time origin and the reference clock's rational rate (Part 01 §§2.2 and 3.9).

    Read from `core.sessions.t_zero_tick` rather than recomputed: the writer took the minimum
    across clocks through R13's mapping, which is arithmetic a reader should not have to repeat
    and would not repeat identically.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    session_id : int, optional
        Which session's origin. Only needed where a multi-session packet's sessions disagree.

    Returns
    -------
    tuple of int
        The origin tick, and the reference rate's numerator and denominator.

    Raises
    ------
    NoTimeOrigin
        If the packet declares none, or if sessions declare different origins and none was
        named. Part 01 §2.2 requires refusing rather than inventing one.
    """
    cache = getattr(packet, "_origin_cache", None)
    if cache is not None and session_id in cache:
        return cache[session_id]  # type: ignore[no-any-return]
    sessions = packet.table("core.sessions")
    if "t_zero_tick" not in sessions.column_names:
        raise NoTimeOrigin("core.sessions carries no t_zero_tick, so seconds are undefined (Part 01 §2.2)")
    declared = {
        session: tick
        for session, tick in zip(
            sessions.column("session_id").to_pylist(), sessions.column("t_zero_tick").to_pylist(), strict=True
        )
        if tick is not None
    }
    if session_id is not None:
        if session_id not in declared:
            raise NoTimeOrigin(f"session {session_id!r} declares no t_zero_tick (Part 01 §2.2)")
        found_tick = int(declared[session_id])
    else:
        found = sorted(set(declared.values()))
        if not found:
            raise NoTimeOrigin("no session declares a t_zero_tick, so seconds are undefined (Part 01 §2.2)")
        if len(found) > 1:
            raise NoTimeOrigin(f"sessions declare different origins {found}; name a session_id")
        found_tick = int(found[0])
    num, den = tick_rate(packet, packet.reference_clock(session_id=session_id))
    if cache is not None:
        cache[session_id] = (found_tick, num, den)
    return (found_tick, num, den)


def on_clock(packet: Any, table: pa.Table, clock: int | None = None, *, bound: float | None = None) -> pa.Table:
    """Return `table` with its ticks on one clock.

    A row whose tick the anchors cannot place is **dropped**, which is what Part 01 §3.9 leaves
    undefined and what `analysis.spike_events` does with the same rows. Reading `core` through
    this and reading the materialized table therefore agree -- which is why the bound defaults to
    the one the packet's writer established and recorded, not the default Part 01 §3.9 states. A reader
    mapping at a narrower bound than the writer used drops rows the packet's own derived table
    kept, and the two disagree about which spikes exist.

    Parameters
    ----------
    packet : Packet
        The packet the table came from, for its anchors and its declared bound.
    table : pyarrow.Table
        Any table carrying `t_tick` and `clock_id`.
    clock : int, optional
        The clock to map onto. Defaults to the packet's reference clock.
    bound : float, optional
        How far from an anchor the mapping stays defined, in median anchor intervals. Defaults
        to :func:`declared_bound`.

    Returns
    -------
    pyarrow.Table
        The same columns, `t_tick` on `clock` and `clock_id` naming it, minus the rows where the
        mapping is undefined.
    """
    if table.num_rows == 0:
        return table
    columns = {name: _flat(table.column(name)) for name in ("t_tick", "clock_id")}
    present = _present(columns["clock_id"])
    target = default_clock(packet, present) if clock is None else clock
    if present == [target]:
        # Already there. Worth the check: it is the whole single-clock case, and it keeps a
        # packet with no anchors readable.
        return table
    limit = declared_bound(packet) if bound is None else bound
    ticks, keep = mapped(pa.record_batch(columns), target, anchors(packet), limit)
    names = table.column_names
    out = table.set_column(names.index("t_tick"), "t_tick", pa.array(ticks))
    # The replacement keeps the column's declared type. A dictionary would change it, and buys
    # nothing on an integer, which is what every identifier is (R53 §2.1).
    clock_column = table.column("clock_id")
    out = out.set_column(
        names.index("clock_id"),
        "clock_id",
        pa.array([target] * table.num_rows, type=clock_column.type),
    )
    return out.filter(pa.array(keep))


def seconds(packet: Any, table: pa.Table, *, session_id: int | None = None) -> pa.Table:
    """Add a `t_second` column to a table whose ticks are on the reference clock.

    Part 01 §2.2: `(t_tick - t_zero_tick) / reference_tick_rate`, taking the rate as the declared
    rational so nothing is lost to the rounded `tick_rate_hz`.

    The tick stays. Seconds are derived and this does not pretend otherwise -- a caller that
    needs to compare, join or bucket still has the exact integer beside the float.

    Seconds may be negative. Data outside its own observation window is a real and reported
    condition (R38 §2.5), and the origin is not clamped to hide it.

    Parameters
    ----------
    packet : Packet
        The packet the table came from, for its origin and reference rate.
    table : pyarrow.Table
        A table carrying `t_tick` and `clock_id`.
    session_id : int, optional
        Which session's origin to use.

    Returns
    -------
    pyarrow.Table
        The same columns plus `t_second`.

    Raises
    ------
    NoTimeOrigin
        If the packet declares no origin.
    NotAligned
        If the table's ticks are not on the reference clock, since seconds from any other
        clock's ticks would be a different quantity wearing the same name.
    """
    start, num, den = origin(packet, session_id)
    reference = packet.reference_clock(session_id=session_id)
    present = _present(_flat(table.column("clock_id"))) if table.num_rows else [reference]
    if present != [reference]:
        raise NotAligned(
            f"seconds are defined on {reference!r} (Part 01 §2.2), but these ticks are on "
            f"{present}; map them with on_clock first"
        )
    offset = pc.subtract(table.column("t_tick"), pa.scalar(start, pa.int64()))
    return table.append_column("t_second", pc.divide(pc.cast(offset, pa.float64()), float(num) / float(den)))
