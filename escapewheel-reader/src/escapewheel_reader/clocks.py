"""Ticks onto one clock, and ticks to seconds.

Over a packet:

- :func:`attach_clocks` -- a table with the clock each of its coordinates is counted on.
- :func:`on_clock` -- a table with its ticks on one clock, without what no anchor places.
- :func:`seconds` -- a table with `t_second` added, from the session's declared origin.
- :func:`clock_columns` -- the column that holds each coordinate's clock.
- :func:`reference_clock` -- the clock a packet reports times on.
- :func:`origin` -- a session's time origin and the reference clock's rational rate.
- :func:`clock_graph` -- each clock's alignment onto its parent, which a tick climbs to its target.
- :func:`anchors`, :func:`declared_bound`, :func:`tick_rate` -- what those are computed from.

Over arrays:

- :func:`align` -- ticks mapped onto a parent clock, and a mask of those it cannot place.
- :func:`rate` -- the parent-to-child rate fitted over an anchor sequence.
- :func:`extrapolation_error` -- :func:`align`'s error beyond the terminal anchors.
- :func:`mapped`, :func:`stored_span`, :func:`default_clock` -- the accessors' and the writer's
  building blocks.

The writer maps with these functions too, so ticks mapped at write time and at read time agree.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from numpy.typing import NDArray

from .dictionaries import values
from .errors import NotAligned, NotDeclared, NoTimeOrigin, Refused, ResourceNotFoundError, Unanchored
from .protocols import Memo, PacketLike
from .resource_ids import CORE_CLOCK_ANCHORS, CORE_CLOCKS, CORE_SESSIONS

#: How far from an anchor the mapping stays defined, as a multiple of the median anchor
#: interval (Part 01 §3.9). One, so that the same threshold covers a gap between anchors and the
#: unanchored ends -- the bound and the region it has to cover are the same quantity, because
#: a free-running sync pulse leaves less than one interval at each end by construction.
BOUND = 1.0

#: Ends every refusal to map: the stored ticks stay readable, each with the clock it was counted on.
_STORED_HINT = "; to read the ticks as stored, pass clock=STORED to an accessor or leave on_clock unset"


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
        The anchor pairs, both strictly increasing.
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
        would then be undefined (Part 01 §3.9).
    """
    return _Map(anchor_t, anchor_p, bound)(np.asarray(ticks, dtype=np.int64))


class _Map:
    """One clock's mapping onto its parent, prepared once and applied to any number of ticks."""

    def __init__(self, anchor_t: Any, anchor_p: Any, bound: float) -> None:
        anchor_t = np.asarray(anchor_t, dtype=np.int64)
        anchor_p = np.asarray(anchor_p, dtype=np.int64)
        if anchor_t.size < 3:
            raise Unanchored(f"{anchor_t.size} anchors define no median interval to bound by")
        if not ((np.diff(anchor_t) > 0).all() and (np.diff(anchor_p) > 0).all()):
            raise ValueError("anchors do not increase together, so interpolation between them is undefined")
        self.anchor_t, self.anchor_p, self.bound = anchor_t, anchor_p, bound
        self.span = float(np.median(np.diff(anchor_t))) * bound
        # A median interval on the parent: what rounding and the fitted ends can move a mapped
        # range by, so :func:`stored_span` widens by it.
        self.slack = float(np.median(np.diff(anchor_p)))
        self.slope, _ = rate(anchor_t, anchor_p)
        # The distance to the nearest anchor, which is what the bound is on, is piecewise linear:
        # zero at each anchor, rising with slope one to the midpoint and falling back. Knots at
        # the anchors and midpoints let np.interp evaluate it, and it is exact, since every slope
        # is one and every knot an integer or a half below 2**53. Past each end it keeps rising
        # to a far knot, beyond which nothing is within any bound.
        far = float(2**52)
        gap = np.diff(anchor_t).astype(np.float64)
        knots = np.empty(2 * anchor_t.size + 1, dtype=np.float64)
        knots[1:-1:2] = anchor_t
        knots[2:-2:2] = anchor_t[:-1] + gap / 2
        knots[0], knots[-1] = anchor_t[0] - far, anchor_t[-1] + far
        distance = np.zeros_like(knots)
        distance[2:-2:2] = gap / 2
        distance[0] = distance[-1] = far
        self.knots, self.distance = knots, distance

    def __call__(self, ticks: NDArray[np.int64]) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
        """Return the parent ticks and whether each is defined, as :func:`align` does."""
        anchor_t, anchor_p = self.anchor_t, self.anchor_p
        # Interior: np.interp is a single C pass doing the search and the lerp together, and is
        # an order of magnitude faster than gathering the bracketing pairs and computing them
        # here; its search starts from the last answer, so ticks in order cost least.
        parent = np.rint(np.interp(ticks, anchor_t, anchor_p)).astype(np.int64)
        # Outside the anchor span np.interp clamps to the terminal value, which is a wrong answer
        # rather than a missing one, so both ends are recomputed with the globally fitted rate,
        # applied from the terminal anchor's own parent tick. The fit's intercept is not
        # used -- it is the one place a line has to represent the whole session's wander at
        # once, and it misses local truth by an amount that does not shrink with distance.
        for end, tick, parent_tick in (
            (ticks < anchor_t[0], anchor_t[0], anchor_p[0]),
            (ticks > anchor_t[-1], anchor_t[-1], anchor_p[-1]),
        ):
            if end.any():
                offsets = (ticks[end] - tick).astype(np.float64)
                parent[end] = parent_tick + np.rint(self.slope * offsets).astype(np.int64)
        return parent, np.interp(ticks, self.knots, self.distance) <= self.span

    def inverse(self) -> _Map:
        """Read the same anchors from parent to child, for widening a range and never for placing a tick."""
        return _Map(self.anchor_p, self.anchor_t, self.bound)


class _Linear:
    """A clock's declared linear transform onto its parent, defined at every tick (Part 01 §3.9)."""

    slack = 1.0

    def __init__(self, slope: float, offset: float) -> None:
        self.slope, self.offset = slope, offset

    def __call__(self, ticks: NDArray[np.int64]) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
        """Return the parent ticks, every one defined."""
        parent = np.rint(self.offset + self.slope * ticks.astype(np.float64)).astype(np.int64)
        return parent, np.ones(ticks.shape, dtype=bool)

    def inverse(self) -> _Linear:
        """Return the transform from parent to child, for widening a range."""
        return _Linear(1.0 / self.slope, -self.offset / self.slope)


class _Path:
    """The edges from one clock up its parent chain to a target, applied in turn.

    Each edge rounds to its parent's tick, as a writer mapping one hop at a time does, and a tick
    is placed only where every edge places it: how far a hop reaches is counted in that clock's
    own median anchor interval (Part 01 §3.9).
    """

    def __init__(self, edges: Sequence[_Map | _Linear]) -> None:
        self.edges = list(edges)

    def __call__(self, ticks: NDArray[np.int64]) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
        """Return the target's ticks and which of them every edge placed."""
        first, *rest = self.edges
        ticks, keep = first(ticks)
        for edge in rest:
            ticks, placed = edge(ticks)
            keep &= placed
        return ticks, keep


@dataclass(frozen=True)
class ClockGraph:
    """Each clock's parent, and the anchors or linear transform that map it there (Part 01 §3.9).

    A tick reaches another clock only by climbing its parent chain: the specification defines
    each mapping onto a parent and none back down, so a target that is not an ancestor is refused
    rather than reached through an inverse.

    Attributes
    ----------
    parents : Mapping
        `clock_id` to `parent_clock_id`, for each clock declaring one.
    anchors : Mapping
        `clock_id` to its anchor ticks and their parent ticks, as :func:`anchors` returns them.
    transforms : Mapping
        `clock_id` to `(transform_slope, transform_offset)`.
    """

    parents: Mapping[int, int]
    anchors: Mapping[int, tuple[NDArray[np.int64], NDArray[np.int64]]]
    transforms: Mapping[int, tuple[float, float]]

    def clocks(self) -> set[int]:
        """Every clock the graph knows of."""
        return {*self.parents, *self.parents.values(), *self.anchors, *self.transforms}

    def ancestry(self, clock: int) -> list[int]:
        """Return the clock, its parent, and so on to the root, stopping where a cycle would repeat."""
        chain = [clock]
        while (parent := self.parents.get(chain[-1])) is not None and parent not in chain:
            chain.append(parent)
        return chain

    def path(self, clock: int, target: int, bound: float) -> _Path:
        """Return the edges from `clock` up to `target`, refusing a target that is not an ancestor."""
        chain = self.ancestry(clock)
        if target not in chain:
            raise NotAligned(
                f"clock {target} is not an ancestor of clock {clock}, whose parent chain is {chain}, and a "
                f"mapping is defined only onto a parent (Part 01 §3.9){_STORED_HINT}"
            )
        try:
            return _Path([self._edge(child, bound) for child in chain[: chain.index(target)]])
        except ValueError as refused:  # NotAligned and Unanchored are both ValueErrors
            raise type(refused)(f"{refused}{_STORED_HINT}") from refused

    def _edge(self, clock: int, bound: float) -> _Map | _Linear:
        if clock in self.transforms:
            return _Linear(*self.transforms[clock])
        if clock in self.anchors:
            return _Map(*self.anchors[clock], bound)
        raise NotAligned(f"{clock} declares neither anchors nor a transform onto its parent {self.parents[clock]}")


def clock_graph(packet: PacketLike) -> ClockGraph:
    """Read each clock's parent and alignment from `core.clocks` and `core.clock_anchors`.

    Kept in the packet's memo, for the same reason :func:`anchors` is. A packet without
    `core.clocks` declares no parents, so its clocks reach nothing but themselves.
    """
    memo = Memo.of(packet)
    if memo.clock_graph is not None:
        return memo.clock_graph
    parents: dict[int, int] = {}
    transforms: dict[int, tuple[float, float]] = {}
    try:
        table = packet.table(CORE_CLOCKS)
    except ResourceNotFoundError:
        table = pa.table({"clock_id": pa.array([], pa.int32())})

    def column(name: str) -> list[Any]:
        return _plain(table.column(name)).to_pylist() if name in table.column_names else [None] * table.num_rows

    # A dozen rows, read into the mappings this returns.
    for clock, parent, slope, offset in zip(
        column("clock_id"),
        column("parent_clock_id"),
        column("transform_slope"),
        column("transform_offset"),
        strict=True,
    ):
        if parent is not None:
            parents[int(clock)] = int(parent)
        if slope is not None and offset is not None:
            transforms[int(clock)] = (float(slope), float(offset))
    graph = ClockGraph(parents, anchors(packet), transforms)
    memo.clock_graph = graph
    return graph


def extrapolation_error(
    anchor_t: NDArray[np.int64],
    anchor_p: NDArray[np.int64],
    distance: float,
) -> dict[str, float]:
    """Measure :func:`align`'s out-of-range estimator at a given distance, in parent ticks.

    Alignment past the terminal anchors is defined only while the estimator's error stays within
    tolerance, and a writer reaching past one median anchor interval measures that error
    (Part 01 §3.9). This is that measurement: every interior anchor stands in for a terminal
    one, the estimator predicts the anchor `distance` median intervals further on, and the
    spread of the residuals is what the tolerance is compared against.

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


def anchors(packet: PacketLike) -> dict[int, tuple[NDArray[np.int64], NDArray[np.int64]]]:
    """Read `core.clock_anchors` into arrays per clock, kept in the packet's memo.

    Kept because an accessor is called per unit, and reading the anchor table for every unit
    would cost more than the spikes do. The table is optional, so a packet without it has no
    anchors.
    """
    memo = Memo.of(packet)
    if memo.anchors is not None:
        return memo.anchors
    try:
        table = packet.table(CORE_CLOCK_ANCHORS)
    except ResourceNotFoundError:
        empty = pa.array([], pa.int64())
        table = pa.table({"clock_id": pa.array([], pa.int32()), "t_tick": empty, "parent_tick": empty})
    clock = np.asarray(_plain(table.column("clock_id")).to_numpy(zero_copy_only=False), dtype=np.int64)
    tick = np.asarray(table.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    parent = np.asarray(table.column("parent_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    # One sort groups the rows by clock and orders each group by tick.
    order = np.lexsort((tick, clock))
    names, starts = np.unique(clock[order], return_index=True)
    groups = np.split(order, starts[1:]) if order.size else []
    out: dict[int, tuple[NDArray[np.int64], NDArray[np.int64]]] = {
        int(name): (tick[rows], parent[rows]) for name, rows in zip(names, groups, strict=True)
    }
    memo.anchors = out
    return out


def declared_bound(packet: PacketLike) -> float:
    """Return the alignment bound the packet's writer established, or `BOUND`.

    `core.sessions.alignment_bound` holds how far past its anchors the writer mapped, and a null
    is the default of one median anchor interval, `BOUND` (Part 02 §12.6). Reading it is what
    makes a consumer's mapping match the writer's: a packet whose spikes were placed at a bound of
    two and whose reader maps at one disagrees with itself about which of its own rows have a
    time.

    Where a packet holds several sessions the widest wins, since the reader presents them as one
    relation and a tick placed under the wider bound has to stay placed.

    Kept in the packet's memo, for the same reason :func:`anchors` is.
    """
    memo = Memo.of(packet)
    if memo.bound is not None:
        return memo.bound

    try:
        sessions = packet.table(CORE_SESSIONS, columns=["alignment_bound"])
    except Exception:  # noqa: BLE001 -- an absent or unreadable table is simply no record
        return BOUND
    declared = [float(v) for v in sessions.column("alignment_bound").to_pylist() if v is not None]
    widest = max([BOUND, *declared])
    memo.bound = widest
    return widest


def reference_clock(packet: PacketLike, *, session_id: int | None = None) -> int:
    """Return the clock a packet reports its times on, `core.sessions.reference_clock_id`.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.
    session_id : int, optional
        Which session's reference to return. Only needed where a multi-session packet's
        sessions disagree, which is refused rather than resolved by picking one.

    Returns
    -------
    int
        The declared `clock_id`.

    Raises
    ------
    NotAligned
        If no session declares one, if the named session does not, or if sessions declare
        different clocks and none was named.
    """
    memo = Memo.of(packet)
    if session_id is None and memo.reference_clock is not None:
        return memo.reference_clock
    table = packet.table(CORE_SESSIONS)
    if "reference_clock_id" not in table.column_names:
        raise NotAligned(f"{CORE_SESSIONS} carries no reference_clock_id")
    declared = {
        session: clock
        for session, clock in zip(
            table.column("session_id").to_pylist(), table.column("reference_clock_id").to_pylist(), strict=True
        )
        if clock is not None
    }
    if session_id is not None:
        if session_id not in declared:
            raise NotAligned(f"session {session_id!r} declares no reference_clock_id")
        return int(declared[session_id])
    named = sorted({int(clock) for clock in declared.values()})
    if not named:
        raise NotAligned("no session declares a reference_clock_id")
    if len(named) > 1:
        raise NotAligned(f"sessions declare different reference clocks {named}; name a session_id")
    memo.reference_clock = named[0]
    return named[0]


def mapped(batch: pa.RecordBatch, target: Any, graph: ClockGraph, bound: float) -> tuple[Any, Any]:
    """Map one batch's ticks onto `target` up each clock's parent chain, returning the ticks and what to keep."""
    ticks = np.asarray(batch.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    clocks = _clock_ids(batch.column("clock_id"))
    parent = np.empty(ticks.size, dtype=np.int64)
    keep = np.zeros(ticks.size, dtype=bool)
    # Every clock's path, prepared before the workers start: a dozen at most, each cheap. A clock
    # that cannot reach the target keeps its refusal, raised only if a row is on it.
    paths: dict[int, _Path | Exception] = {}
    for name in graph.clocks() | {int(target)}:
        try:
            paths[name] = graph.path(name, int(target), bound)
        except (NotAligned, ValueError) as refused:  # Unanchored is a ValueError
            paths[name] = refused

    def run(lo: int, hi: int) -> None:
        chunk = clocks[lo:hi]
        # Rows cluster by unit and a unit has one clock, so a chunk is ordinarily on one clock
        # and maps as a slice, gathering nothing.
        first = chunk[0]
        groups: list[tuple[int, Any]] = [(int(first), slice(lo, hi))] if (chunk == first).all() else []
        if not groups:
            for name in np.unique(chunk).tolist():
                groups.append((name, lo + np.flatnonzero(chunk == name)))
        for name, rows in groups:
            if name == _NULL_CLOCK:  # a null clock places nothing
                continue
            prepared = paths[name] if name in paths else graph.path(name, int(target), bound)
            if isinstance(prepared, Exception):
                raise prepared
            if not prepared.edges:
                parent[rows], keep[rows] = ticks[rows], True
            else:
                parent[rows], keep[rows] = prepared(ticks[rows])

    bounds = list(range(0, ticks.size, _CHUNK_ROWS))
    if len(bounds) <= 1:
        if ticks.size:
            run(0, ticks.size)
        return parent, keep
    with ThreadPoolExecutor(min(len(bounds), os.cpu_count() or 1)) as pool:
        # list() so that a worker's exception reaches the caller.
        list(pool.map(lambda lo: run(lo, min(lo + _CHUNK_ROWS, ticks.size)), bounds))
    return parent, keep


#: Rows a worker maps at once: large enough that a chunk's fixed cost is noise, small enough that
#: a large batch spreads across every core.
_CHUNK_ROWS = 1 << 20


#: Stands in for a null clock, below any int32 identifier.
_NULL_CLOCK = -(2**62)


def _clock_ids(column: Any) -> NDArray[np.int64]:
    """Return each row's clock ID as int64, a null as `_NULL_CLOCK`.

    An identifier is an integer, so the ID is its own group key and nothing is hashed.
    """
    if pa.types.is_dictionary(column.type):
        column = column.dictionary.take(column.indices)
    if column.null_count:
        column = pc.fill_null(column.cast(pa.int64()), _NULL_CLOCK)
    return np.asarray(column.to_numpy(zero_copy_only=False), dtype=np.int64)


def stored_span(graph: ClockGraph, target: int, span: tuple[int, int]) -> tuple[int, int]:
    """Widen a range on `target` into one that covers it on every stored clock.

    A constraint a caller states on the reference clock has to reach the file as a constraint
    on the ticks the file holds, and each clock maps differently, so the pushed range is the
    union over clocks. It is deliberately loose: its only job is to let row groups that cannot
    match go unread, and the exact range is applied after mapping, where every row is on one
    clock and the comparison means something.
    """
    lo, hi = span
    lows, highs = [lo], [hi]
    for clock in graph.clocks() - {target}:
        try:
            path = graph.path(clock, target, BOUND)
        except (NotAligned, ValueError):
            continue  # its rows cannot reach the target, and mapping them refuses
        ends = np.array([lo, hi], dtype=np.int64)
        # Down the chain through each edge read the other way, widening by a median interval
        # per hop: that covers the rounding and the fitted ends the forward map applies.
        for edge in reversed(path.edges):
            inverse = edge.inverse()
            ends = inverse(ends)[0]
            slack = int(np.ceil(inverse.slack))
            ends = np.array([ends[0] - slack, ends[1] + slack], dtype=np.int64)
        lows.append(int(ends[0]))
        highs.append(int(ends[1]))
    return min(lows), max(highs)


# -- (packet, table) semantics ------------------------------------------------------------
#
# These take a packet and a table and return a table. They are free functions rather than
# methods because our currency is `pa.Table`, which is PyArrow's and has no `.pipe()`: a method
# for one would sit on the packet and operate on a table, owned by neither.


def _present(column: Any) -> list[int]:
    """Distinct clock IDs in a column, read from its dictionary where it has one.

    A min and max answer the ordinary case of one clock without hashing every row.
    """
    if not pa.types.is_dictionary(column.type) and len(column):
        least, most = pc.min_max(column).values()
        if least.as_py() == most.as_py():
            return [] if least.as_py() is None else [int(least.as_py())]
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


def default_clock(packet: PacketLike, present: list[int]) -> int:
    """Return the clock to map onto when the caller named none.

    The declared reference. Where a packet declares none: the one clock the rows are already on,
    since there is then nothing to reconcile; else the root every row's clock climbs to, the one
    clock they all reach. Rows whose clocks reach different roots are refused: returning them as
    stored invites a comparison that means nothing.
    """
    try:
        return reference_clock(packet)
    except NotAligned as undeclared:
        if len(present) == 1:
            return present[0]
        graph = clock_graph(packet)
        roots = sorted({graph.ancestry(clock)[-1] for clock in present})
        if len(roots) == 1:
            return roots[0]
        raise NotAligned(
            f"{undeclared}, and the rows' clocks {present} climb to different roots {roots}{_STORED_HINT}"
        ) from undeclared


def tick_rate(packet: PacketLike, clock_id: int) -> tuple[int, int]:
    """Return a clock's declared rational tick rate."""
    clocks = packet.table(CORE_CLOCKS)
    names = clocks.column("clock_id").to_pylist()
    if clock_id not in names:
        raise NotAligned(f"{CORE_CLOCKS} declares no {clock_id!r}, so its rate is unknown")
    row = names.index(clock_id)
    num = clocks.column("tick_rate_num")[row].as_py()
    den = clocks.column("tick_rate_den")[row].as_py() if "tick_rate_den" in clocks.column_names else 1
    if not num:
        raise NotAligned(f"{clock_id!r} declares no tick_rate_num, so seconds cannot be derived")
    return int(num), int(den or 1)


def origin(packet: PacketLike, session_id: int | None = None) -> tuple[int, int, int]:
    """Return the session's time origin and the reference clock's rational rate (Part 01 §2.2).

    Read from `core.sessions.t_zero_tick` rather than recomputed: the writer took the earliest
    observation start across clocks through the anchor mapping, which is arithmetic a reader
    should not have to repeat and would not repeat identically.

    Parameters
    ----------
    packet : PacketLike
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
        named: an origin is refused rather than invented.
    """
    origins = Memo.of(packet).origins
    if session_id in origins:
        return origins[session_id]
    sessions = packet.table(CORE_SESSIONS)
    if "t_zero_tick" not in sessions.column_names:
        raise NoTimeOrigin(f"{CORE_SESSIONS} carries no t_zero_tick, so seconds are undefined")
    declared = {
        session: tick
        for session, tick in zip(
            sessions.column("session_id").to_pylist(), sessions.column("t_zero_tick").to_pylist(), strict=True
        )
        if tick is not None
    }
    if session_id is not None:
        if session_id not in declared:
            raise NoTimeOrigin(f"session {session_id!r} declares no t_zero_tick")
        found_tick = int(declared[session_id])
    else:
        found = sorted(set(declared.values()))
        if not found:
            raise NoTimeOrigin("no session declares a t_zero_tick, so seconds are undefined")
        if len(found) > 1:
            raise NoTimeOrigin(f"sessions declare different origins {found}; name a session_id")
        found_tick = int(found[0])
    num, den = tick_rate(packet, reference_clock(packet, session_id=session_id))
    origins[session_id] = (found_tick, num, den)
    return origins[session_id]


def _declared_table(packet: PacketLike, resource_id: str) -> Mapping[str, Any]:
    """Return the table a resource's declaration describes, from whichever bound registry holds it."""
    declaration = packet.resource(resource_id).declaration
    table = declaration.get("table") if isinstance(declaration, Mapping) else None
    if not isinstance(table, Mapping):
        raise NotDeclared(f"no bound registry declares {resource_id} as a table")
    return table


def _clock_sources(declared: Mapping[str, Any]) -> dict[str, str]:
    """Map each coordinate column to the `clock_from` naming its clock (Part 02 §8.4)."""
    return {
        column["name"]: column.get("clock_from", "clock_id")
        for column in declared.get("columns", [])
        if column.get("role") == "coordinate"
    }


def clock_columns(packet: PacketLike, resource_id: str) -> dict[str, str]:
    """Name the column that holds each coordinate's clock once :func:`attach_clocks` has run.

    A coordinate on the table's own `clock_id` keeps it. Where the table declares no `clock_id`
    and every coordinate takes its clock from one place, that clock is `clock_id`; otherwise a
    coordinate reaching its clock elsewhere gets `<coordinate>_clock_id`. Derived from the
    declaration alone, so the names do not depend on which columns a read selected.

    Parameters
    ----------
    packet : PacketLike
        The packet whose bound registries declare the resource.
    resource_id : str
        The table resource, core or extension.

    Returns
    -------
    dict
        Coordinate column to clock column, in declaration order.

    Raises
    ------
    NotDeclared
        If no bound registry declares the table, or a coordinate without `clock_from` sits in a
        table with no `clock_id`.
    Refused
        If the name a clock would take is already a declared column, which it would overwrite.
    """
    declared = _declared_table(packet, resource_id)
    names = {column["name"] for column in declared.get("columns", [])}
    sources = _clock_sources(declared)
    shared = "clock_id" not in names and len(set(sources.values())) == 1
    out = {}
    for coordinate, source in sources.items():
        if source == "clock_id":
            if "clock_id" not in names:
                raise NotDeclared(f"{resource_id}.{coordinate} names no clock_from and the table declares no clock_id")
            out[coordinate] = "clock_id"
            continue
        name = "clock_id" if shared else f"{coordinate}_clock_id"
        if name in names:
            raise Refused(f"{resource_id} declares {name}, so the clock of {coordinate} has no column to go in")
        out[coordinate] = name
    return out


def attach_clocks(packet: PacketLike, resource_id: str, table: pa.Table) -> pa.Table:
    """Add the clock each coordinate column's ticks are counted on, as the declaration says.

    A coordinate's clock is its `clock_from` target where declared, else the row's `clock_id`
    (Part 02 §8.4). A target in another table is read through the one reference this table
    declares to it, taking only that table's key and clock columns for the keys present. A row
    whose key finds no target row gets a null clock. :func:`clock_columns` names the added
    columns; one already in `table` is kept, so attaching twice is attaching once.

    Parameters
    ----------
    packet : PacketLike
        The packet the table came from.
    resource_id : str
        The table's resource, whose declaration says where each clock is.
    table : pyarrow.Table
        Rows of that resource. Only coordinates it carries get a clock, and each needs the
        columns its clock is reached through.

    Returns
    -------
    pyarrow.Table
        `table` with the clock columns appended.

    Raises
    ------
    NotDeclared
        If `clock_from` names a table this one does not reference exactly once.
    ValueError
        If `table` lacks a column a clock is reached through.
    """
    declared = _declared_table(packet, resource_id)
    named = clock_columns(packet, resource_id)
    for coordinate, source in _clock_sources(declared).items():
        if coordinate in table.column_names and named[coordinate] not in table.column_names:
            table = table.append_column(named[coordinate], _clock_of(packet, resource_id, declared, source, table))
    return table


def _clock_of(packet: PacketLike, resource_id: str, declared: Mapping[str, Any], source: str, table: pa.Table) -> Any:
    """Read the clock `source` names for each row of `table`, null where the hop finds no row."""
    target_resource, _, target = source.rpartition(".")
    if not target_resource:
        if source not in table.column_names:
            raise ValueError(f"the clock of {resource_id} is its {source}, which the table does not carry")
        return table.column(source)
    references = [r for r in declared.get("references", []) if r["resource"] == target_resource]
    if len(references) != 1:
        raise NotDeclared(
            f"{resource_id} declares {len(references)} references to {target_resource}, "
            f"so clock_from {source} names no single row"
        )
    keys, target_keys = references[0]["columns"], references[0]["resource_columns"]
    missing = [key for key in keys if key not in table.column_names]
    if missing:
        raise ValueError(f"the clock of {resource_id} is reached through {missing}, which the table does not carry")
    local = [_plain(table.column(key)) for key in keys]
    # Narrowed to the keys present: a parent such as `core.units` is small, but reading it whole
    # per call is what an accessor called per unit cannot afford.
    narrow: dict[str, Any] = {
        name: [v for v in pc.unique(column).to_pylist() if v is not None]
        for name, column in zip(target_keys, local, strict=True)
    }
    found = packet.table(target_resource, columns=list(dict.fromkeys([*target_keys, target])), **narrow)
    local = [column.cast(found.column(name).type) for column, name in zip(local, target_keys, strict=True)]
    if len(keys) == 1:
        position = pc.index_in(local[0], value_set=_flat(found.column(target_keys[0])))
        return pc.take(found.column(target), position)
    # Composite keys: a left join keeps every row and an unmatched one null, and the row number
    # restores the order the join does not keep.
    joined_on = [f"k{i}" for i in range(len(keys))]
    left = pa.table({**dict(zip(joined_on, local, strict=True)), "row": pa.array(np.arange(table.num_rows))})
    parent = {k: found.column(name) for k, name in zip(joined_on, target_keys, strict=True)}
    right = pa.table({**parent, "clock": found.column(target)})
    joined = left.join(right, keys=joined_on, join_type="left outer").sort_by("row")
    if joined.num_rows != table.num_rows:
        raise Refused(f"{target_resource} holds a key {resource_id} references more than once")
    return joined.column("clock")


def _plain(column: Any) -> Any:
    """Decode a dictionary column, so it compares against the parent's plain key."""
    return column.cast(column.type.value_type) if pa.types.is_dictionary(column.type) else column


def _placed(
    ticks: Any, clock: Any, target: int, graph: ClockGraph, bound: float
) -> tuple[pa.Array[Any], NDArray[np.bool_]]:
    """Map one coordinate onto `target`, nulling what cannot be placed.

    Returns the mapped column and which rows to keep: a null tick has nothing to place and is
    kept, and a tick on a null clock cannot be placed.
    """
    ticks, clock = _flat(ticks), _flat(clock)
    if not ticks.null_count and not clock.null_count:
        # Nothing null, so nothing to gather around.
        parent, placed = mapped(pa.record_batch({"t_tick": ticks, "clock_id": clock}), target, graph, bound)
        return _ticks(parent, placed, ticks.type), placed
    known = pc.and_(pc.is_valid(ticks), pc.is_valid(clock)).to_numpy(zero_copy_only=False)
    parent = np.zeros(len(ticks), dtype=np.int64)
    placed = np.zeros(len(ticks), dtype=bool)
    rows = np.flatnonzero(known)
    if rows.size:
        batch = pa.record_batch({"t_tick": ticks.take(rows), "clock_id": clock.take(rows)})
        parent[rows], placed[rows] = mapped(batch, target, graph, bound)
    absent = pc.is_null(ticks).to_numpy(zero_copy_only=False)
    return _ticks(parent, placed, ticks.type), placed | absent


def _ticks(parent: NDArray[np.int64], placed: NDArray[np.bool_], kind: pa.DataType) -> pa.Array[Any]:
    """Wrap mapped ticks as the column's type, null where unplaced, copying only what that needs."""
    out = pa.array(parent) if placed.all() else pa.array(parent, mask=~placed)
    return out if out.type == kind else out.cast(kind)


def _on_target(
    packet: PacketLike,
    table: pa.Table,
    by_column: Mapping[str, list[str]],
    drop: bool,
    clock: int | None,
    bound: float | None,
) -> pa.Table:
    """Map each coordinate through its clock column onto one clock, the one path every caller takes.

    `by_column` names the coordinates counted on each clock column. With `drop`, a row any
    coordinate cannot place goes: one coordinate is a row's whole content, as `analysis.spike_events`
    omits it. Otherwise only the cell is nulled and the row's other coordinates stay worth having.
    """
    if not by_column or table.num_rows == 0:
        return table
    flat = {column: _flat(table.column(column)) for column in by_column}
    present_by_column = {column: _present(values) for column, values in flat.items()}
    present = sorted({value for values in present_by_column.values() for value in values})
    target = default_clock(packet, present) if clock is None else clock
    keep: NDArray[np.bool_] | None = None
    limit = declared_bound(packet) if bound is None else bound
    for column, coordinates in by_column.items():
        clock_column = flat[column]
        if present_by_column[column] == [target] and not clock_column.null_count:
            # Already there: the whole single-clock case, and what keeps a packet with no anchors
            # readable.
            continue
        graph = clock_graph(packet)
        for coordinate in coordinates:
            ticks, placed = _placed(table.column(coordinate), clock_column, target, graph, limit)
            if drop:
                keep = placed if keep is None else keep & placed
            table = table.set_column(table.column_names.index(coordinate), coordinate, ticks)
        kind = _plain(clock_column).type
        if clock_column.null_count:
            on_target = pc.if_else(pc.is_valid(clock_column), pa.scalar(target, kind), pa.scalar(None, kind))
        else:
            on_target = pa.repeat(pa.scalar(target, kind), table.num_rows)
        # The column keeps its declared type; a dictionary of one value buys nothing on an integer.
        declared_type = table.schema.field(column).type
        table = table.set_column(table.column_names.index(column), column, on_target.cast(declared_type))
    return table if keep is None or keep.all() else table.filter(pa.array(keep))


def on_clock(
    packet: PacketLike,
    table: pa.Table,
    clock: int | None = None,
    *,
    resource_id: str | None = None,
    bound: float | None = None,
) -> pa.Table:
    """Return `table` with its ticks on one clock.

    A row whose tick the anchors cannot place is **dropped**: the mapping is undefined there
    (Part 01 §3.9), and `analysis.spike_events` omits the same rows. Reading `core` through this
    and reading the materialized table therefore agree -- which is why the bound defaults to the
    one the packet's writer established and recorded, not to `BOUND`. A reader mapping at a
    narrower bound than the writer used drops rows the packet's own derived table kept, and the
    two disagree about which spikes exist.

    With `resource_id`, every coordinate the resource declares is mapped, each through the clock
    :func:`attach_clocks` gives it, and that clock column then names `clock`. A resource with one
    coordinate drops a row it cannot place, as above. A resource with several nulls the one cell
    and keeps the row, whose other coordinates may still place.

    Parameters
    ----------
    packet : PacketLike
        The packet the table came from, for its anchors and its declared bound.
    table : pyarrow.Table
        Any table carrying `t_tick` and `clock_id`, or with `resource_id` rows of that resource.
    clock : int, optional
        The clock to map onto. Defaults to the packet's reference clock.
    resource_id : str, optional
        The resource the rows are of, whose declaration says which columns are coordinates and
        where each one's clock is.
    bound : float, optional
        How far from an anchor the mapping stays defined, in median anchor intervals. Defaults
        to :func:`declared_bound`.

    Returns
    -------
    pyarrow.Table
        The same columns, `t_tick` on `clock` and `clock_id` naming it, minus the rows where the
        mapping is undefined. With `resource_id`, plus any clock column attached.

    Raises
    ------
    NotAligned
        If a clock the rows are on has no anchors, so no path reaches `clock`.
    """
    if resource_id is None:
        # A bare table is one coordinate, `t_tick`, on its own `clock_id`.
        return _on_target(packet, table, {"clock_id": ["t_tick"]}, True, clock, bound)
    table = attach_clocks(packet, resource_id, table)
    declared = clock_columns(packet, resource_id)
    by_column: dict[str, list[str]] = {}
    for coordinate, column in declared.items():
        if coordinate in table.column_names:
            by_column.setdefault(column, []).append(coordinate)
    return _on_target(packet, table, by_column, len(declared) == 1, clock, bound)


def seconds(
    packet: PacketLike, table: pa.Table, *, resource_id: str | None = None, session_id: int | None = None
) -> pa.Table:
    """Add a `t_second` column to a table whose ticks are on the reference clock.

    Part 01 §2.2: `(t_tick - t_zero_tick) / reference_tick_rate`, taking the rate as the declared
    rational so nothing is lost to the rounded `tick_rate_hz`.

    The tick stays. Seconds are derived and this does not pretend otherwise -- a caller that
    needs to compare, join or bucket still has the exact integer beside the float.

    Seconds may be negative. A tick before the origin is a real condition, which the registry's
    `within_observation` rules report, and the origin is not clamped to hide it.

    With `resource_id`, each coordinate the resource declares gets its own column, `<name>_tick`
    becoming `<name>_second`, and each is checked against the clock :func:`attach_clocks` gives
    it. A null tick is a null second.

    Parameters
    ----------
    packet : PacketLike
        The packet the table came from, for its origin and reference rate.
    table : pyarrow.Table
        A table carrying `t_tick` and `clock_id`, or with `resource_id` rows of that resource.
    resource_id : str, optional
        The resource the rows are of, whose declaration says which columns are coordinates.
    session_id : int, optional
        Which session's origin to use.

    Returns
    -------
    pyarrow.Table
        The same columns plus `t_second`, or with `resource_id` any clock column attached and a
        seconds column per coordinate.

    Raises
    ------
    NoTimeOrigin
        If the packet declares no origin.
    NotAligned
        If the table's ticks are not on the reference clock, since seconds from any other
        clock's ticks would be a different quantity wearing the same name.
    Refused
        If a seconds column's name is already taken.
    """
    start, num, den = origin(packet, session_id)
    reference = reference_clock(packet, session_id=session_id)
    if resource_id is None:
        pairs = {"t_tick": "clock_id"}
    else:
        table = attach_clocks(packet, resource_id, table)
        pairs = {c: k for c, k in clock_columns(packet, resource_id).items() if c in table.column_names}
    for clock_column in dict.fromkeys(pairs.values()):
        present = _present(_flat(table.column(clock_column))) if table.num_rows else []
        if present not in ([], [reference]):
            raise NotAligned(
                f"seconds are defined on {reference!r}, but these ticks are on {present}; map them with on_clock first"
            )
    for coordinate in pairs:
        name = f"{coordinate.removesuffix('_tick')}_second"
        if name in table.column_names:
            raise Refused(f"the table already carries {name}")
        offset = pc.subtract(table.column(coordinate), pa.scalar(start, pa.int64()))
        table = table.append_column(name, pc.divide(pc.cast(offset, pa.float64()), float(num) / float(den)))
    return table


__all__ = [
    "BOUND",
    "ClockGraph",
    "align",
    "anchors",
    "attach_clocks",
    "clock_columns",
    "clock_graph",
    "declared_bound",
    "extrapolation_error",
    "mapped",
    "on_clock",
    "origin",
    "reference_clock",
    "seconds",
]
