"""Ticks onto one clock, and ticks to seconds.

Over a packet:

- :func:`attach_clocks` -- a table with the clock each of its coordinates is counted on.
- :func:`on_clock` -- a table with its ticks on one clock, without what no anchor places.
- :func:`seconds` -- a table with `t_second` added, from the session's declared origin.
- :func:`seconds_expression` -- the same seconds as an expression a scan can project.
- :func:`clock_columns` -- the column that holds each coordinate's clock.
- :func:`reference_clock` -- the clock a packet reports times on.
- :func:`origin` -- a session's time origin and the reference clock's rational rate.
- :func:`clock_graph` -- each clock's alignment onto its parent, which a tick climbs to its target.
- :func:`anchors`, :func:`declared_bound`, :func:`tick_rate` -- what those are computed from.

Over arrays:

- :func:`align` -- ticks mapped onto a parent clock, and a mask of those it cannot place.
- :func:`rate` -- the parent-to-child rate fitted over an anchor sequence.
- :func:`extrapolation_error` -- :func:`align`'s error beyond the terminal anchors.
- :func:`mapped`, :func:`stored_intervals`, :func:`default_clock` -- the accessors' and the
  writer's building blocks.

The writer maps with these functions too, so ticks mapped at write time and at read time agree.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, cast, overload

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as pads
from numpy.typing import NDArray

from .dictionaries import lookup, values
from .errors import NotAligned, NotDeclared, NoTimeOrigin, Refused, ResourceNotFoundError, Unanchored
from .optional import read_optional
from .protocols import Memo, PacketLike, PacketSetLike
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
        # No tick between the first and last anchor lies farther than half a gap from one.
        self.holes = bool(gap.max(initial=0.0) / 2 > self.span)

    def __call__(self, ticks: NDArray[np.int64]) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
        """Return the parent ticks and whether each is defined, as :func:`align` does."""
        anchor_t, anchor_p = self.anchor_t, self.anchor_p
        # Interior: np.interp is a single C pass doing the search and the lerp together, and is
        # an order of magnitude faster than gathering the bracketing pairs and computing them
        # here; its search starts from the last answer, so ticks in order cost least.
        parent = np.rint(np.interp(ticks, anchor_t, anchor_p)).astype(np.int64)
        # Without a hole every tick between the end anchors is placed, and one past an end is
        # placed within the span of it, so the distance need not be interpolated at all.
        keep = None if self.holes else np.ones(ticks.size, dtype=bool)
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
                if keep is not None:
                    keep[end] = np.abs(offsets) <= self.span
        return parent, np.interp(ticks, self.knots, self.distance) <= self.span if keep is None else keep

    def reach(self) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        """Return the closed tick intervals this map places, found against :meth:`__call__` itself.

        The distance to the nearest anchor rises from each anchor to the midpoint of its gap and
        falls after it, so each half holds one boundary, and a gap wider than twice the span is a
        hole.
        """
        anchor_t = self.anchor_t
        margin = int(np.ceil(self.span)) + 1

        def placed(ticks: NDArray[np.int64]) -> NDArray[np.bool_]:
            return self(ticks)[1]

        def unplaced(ticks: NDArray[np.int64]) -> NDArray[np.bool_]:
            return ~self(ticks)[1]

        first = _least(placed, anchor_t[:1] - margin, anchor_t[:1])
        beyond = _least(unplaced, anchor_t[-1:], anchor_t[-1:] + margin)
        middle = anchor_t[:-1] + np.diff(anchor_t) // 2
        hole_start = _least(unplaced, anchor_t[:-1], middle)
        hole_stop = _least(placed, middle, anchor_t[1:])
        holes = hole_start <= middle
        return np.concatenate([first, hole_stop[holes]]), np.concatenate([hole_start[holes] - 1, beyond - 1])


class _Linear:
    """A clock's declared linear transform onto its parent, defined at every tick (Part 01 §3.9)."""

    def __init__(self, slope: float, offset: float) -> None:
        self.slope, self.offset = slope, offset

    def __call__(self, ticks: NDArray[np.int64]) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
        """Return the parent ticks, every one defined."""
        parent = np.rint(self.offset + self.slope * ticks.astype(np.float64)).astype(np.int64)
        return parent, np.ones(ticks.shape, dtype=bool)

    def reach(self) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        """Return every tick within 2**53 whose parent tick fits in int64, the one interval it places."""
        limit = float(2**62)
        low = max(-(2**53), int(np.ceil((-limit - self.offset) / self.slope)))
        high = min(2**53, int(np.floor((limit - self.offset) / self.slope)))
        return np.array([low], dtype=np.int64), np.array([high], dtype=np.int64)


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
    #: Each edge as built, by clock and bound, so a stream mapping batch by batch builds it once.
    _edges: dict[tuple[int, float], _Map | _Linear] = field(default_factory=dict, compare=False, repr=False)

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
        if (built := self._edges.get((clock, bound))) is not None:
            return built
        if clock in self.transforms:
            edge: _Map | _Linear = _Linear(*self.transforms[clock])
        elif clock in self.anchors:
            edge = _Map(*self.anchors[clock], bound)
        else:
            raise NotAligned(f"{clock} declares neither anchors nor a transform onto its parent {self.parents[clock]}")
        self._edges[(clock, bound)] = edge
        return edge


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
    names = ["clock_id", "parent_clock_id", "transform_slope", "transform_offset"]
    table = read_optional(packet, CORE_CLOCKS, names)
    # A dozen rows, read into the mappings this returns.
    for clock, parent, slope, offset in zip(*(_plain(table.column(n)).to_pylist() for n in names), strict=True):
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
    declared = pc.max(sessions.column("alignment_bound")).as_py()
    widest = BOUND if declared is None else max(BOUND, float(declared))
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
    found = _session_value(packet, "reference_clock_id", session_id, NotAligned)
    if session_id is None:
        memo.reference_clock = found
    return found


def _session_value(packet: PacketLike, column: str, session_id: int | None, refusal: type[Exception]) -> int:
    """Return the `column` one session declares, or the one value every declaring session agrees on.

    A multi-session packet whose sessions disagree is refused rather than resolved by picking one.
    """
    sessions = read_optional(packet, CORE_SESSIONS, ["session_id", column])
    declared = sessions.filter(pc.is_valid(sessions.column(column)))
    if session_id is not None:
        ids = _plain(declared.column("session_id"))
        declared = declared.filter(pc.equal(ids, pa.scalar(session_id, ids.type)))
        if not declared.num_rows:
            raise refusal(f"session {session_id!r} declares no {column}")
    found = sorted(pc.unique(_plain(declared.column(column))).to_pylist())
    if not found:
        raise refusal(f"no session declares a {column}")
    if len(found) > 1:
        raise refusal(f"sessions declare different values of {column}, {found}; name a session_id")
    return int(found[0])


def mapped(batch: pa.RecordBatch, target: Any, graph: ClockGraph, bound: float) -> tuple[Any, Any]:
    """Map one batch's ticks onto `target` up each clock's parent chain, returning the ticks and what to keep."""
    ticks = np.asarray(batch.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    clocks = _clock_ids(batch.column("clock_id"))
    pieces = [
        (lo, ticks[lo : lo + _CHUNK_ROWS], clocks[lo : lo + _CHUNK_ROWS]) for lo in range(0, ticks.size, _CHUNK_ROWS)
    ]
    return _mapped(pieces, ticks.size, target, graph, bound)


def _mapped(
    pieces: Sequence[tuple[int, NDArray[Any], NDArray[Any]]], rows: int, target: Any, graph: ClockGraph, bound: float
) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
    """Map pieces of `rows` ticks, each its row offset, ticks and clock IDs, in parallel into one result."""
    parent = np.empty(rows, dtype=np.int64)
    keep = np.zeros(rows, dtype=bool)
    # Every clock's path, prepared before the workers start: a dozen at most, each cheap. A clock
    # that cannot reach the target keeps its refusal, raised only if a row is on it.
    paths: dict[int, _Path | Exception] = {}
    for name in graph.clocks() | {int(target)}:
        try:
            paths[name] = graph.path(name, int(target), bound)
        except (NotAligned, ValueError) as refused:  # Unanchored is a ValueError
            paths[name] = refused

    def run(piece: tuple[int, NDArray[Any], NDArray[Any]]) -> None:
        lo, ticks, chunk = piece
        if not ticks.size:
            return
        # Rows cluster by unit and a unit has one clock, so a chunk is ordinarily on one clock
        # and maps as a slice, gathering nothing.
        first = chunk[0]
        groups: list[tuple[int, Any]] = [(int(first), slice(None))] if (chunk == first).all() else []
        if not groups:
            for name in np.unique(chunk).tolist():
                groups.append((name, np.flatnonzero(chunk == name)))
        for name, local in groups:
            if name == _NULL_CLOCK:  # a null clock places nothing
                continue
            prepared = paths[name] if name in paths else graph.path(name, int(target), bound)
            if isinstance(prepared, Exception):
                raise prepared
            rows_out = slice(lo, lo + ticks.size) if isinstance(local, slice) else lo + local
            if not prepared.edges:
                parent[rows_out], keep[rows_out] = ticks[local], True
            else:
                parent[rows_out], keep[rows_out] = prepared(ticks[local])

    if len(pieces) <= 1:
        for piece in pieces:
            run(piece)
        return parent, keep
    with ThreadPoolExecutor(min(len(pieces), os.cpu_count() or 1)) as pool:
        # list() so that a worker's exception reaches the caller.
        list(pool.map(run, pieces))
    return parent, keep


def _pieces(ticks: Any, clock: Any) -> list[tuple[int, NDArray[Any], NDArray[Any]]]:
    """Split null-free ticks and clocks into work for :func:`_mapped`, reading each tick chunk in place.

    Copying hundreds of millions of ticks into one array costs a third of mapping them, so each
    chunk is a piece of its own unless the chunks are too small to be worth a task.
    """
    clocks = _clock_ids(_flat(clock))
    chunks = ticks.chunks if isinstance(ticks, pa.ChunkedArray) else [ticks]
    if len(chunks) > 1 and len(clocks) / len(chunks) < _CHUNK_ROWS // 16:
        chunks = [_flat(ticks)]
    pieces, offset = [], 0
    for chunk in chunks:
        flat = np.asarray(chunk.to_numpy(zero_copy_only=False), dtype=np.int64)
        for lo in range(0, flat.size, _CHUNK_ROWS):
            hi = min(lo + _CHUNK_ROWS, flat.size)
            pieces.append((offset + lo, flat[lo:hi], clocks[offset + lo : offset + hi]))
        offset += flat.size
    return pieces


#: Rows a worker maps at once: large enough that a chunk's fixed cost is noise, small enough that
#: a large batch spreads across every core.
_CHUNK_ROWS = 1 << 20


#: Stands in for a null clock, below any int32 identifier.
_NULL_CLOCK = -(2**62)


def _clock_ids(column: Any) -> NDArray[np.integer[Any]]:
    """Return each row's clock ID in its stored width, a null as `_NULL_CLOCK` in int64.

    An identifier is an integer, so the ID is its own group key and nothing is hashed.
    """
    if pa.types.is_dictionary(column.type):
        column = column.dictionary.take(column.indices)
    if column.null_count:
        column = pc.fill_null(column.cast(pa.int64()), _NULL_CLOCK)
    return np.asarray(column.to_numpy(zero_copy_only=False))


def stored_intervals(
    graph: ClockGraph, clock: int, target: int, span: tuple[int, int], bound: float
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Return the closed intervals of `clock`'s ticks that map into `span` on `target`.

    Exact: a stored tick lies in an interval if and only if :func:`mapped` places it and its mapped
    tick lies in `span`. Every edge is monotone, since anchors increase together and a transform's
    slope is positive (Part 01 §3.9), so the ticks an edge sends into an interval form one
    interval, found by bisecting the edge itself and then cut to what it places.

    Raises
    ------
    NotAligned, Unanchored, ValueError
        As :meth:`ClockGraph.path` does, including for anchors that do not increase, where the
        inverse would be wrong.
    """
    starts = np.array([span[0]], dtype=np.int64)
    stops = np.array([span[1]], dtype=np.int64)
    for edge in reversed(graph.path(clock, target, bound).edges):
        starts, stops = _preimage(edge, starts[starts <= stops], stops[starts <= stops])
    keep = starts <= stops
    return starts[keep], stops[keep]


def _preimage(
    edge: _Map | _Linear, starts: NDArray[np.int64], stops: NDArray[np.int64]
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Return the ticks `edge` places onto the closed intervals `starts` to `stops`, as closed intervals."""
    reach_starts, reach_stops = edge.reach()
    low = np.full(starts.shape, reach_starts[0], dtype=np.int64)
    high = np.full(starts.shape, reach_stops[-1], dtype=np.int64)
    first = _least(lambda ticks: edge(ticks)[0] >= starts, low, high)
    last = _least(lambda ticks: edge(ticks)[0] > stops, low, high) - 1
    # Each preimage cut to each interval the edge places; a few of each, so pairwise is cheap.
    cut_starts = np.maximum(first[:, None], reach_starts[None, :]).ravel()
    cut_stops = np.minimum(last[:, None], reach_stops[None, :]).ravel()
    keep = cut_starts <= cut_stops
    order = np.argsort(cut_starts[keep], kind="stable")
    return cut_starts[keep][order], cut_stops[keep][order]


def _least(
    holds: Callable[[NDArray[np.int64]], NDArray[np.bool_]], low: NDArray[np.int64], high: NDArray[np.int64]
) -> NDArray[np.int64]:
    """Return the least tick in each closed `[low, high]` where `holds` does, or `high + 1` where none does.

    `holds` must turn from False to True at most once across each interval.
    """
    low = np.array(low, dtype=np.int64)
    high = np.array(high, dtype=np.int64) + 1
    while (active := low < high).any():
        middle = low + (high - low) // 2
        found = holds(middle)
        high = np.where(active & found, middle, high)
        low = np.where(active & ~found, middle + 1, low)
    return low


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
    clocks = read_optional(packet, CORE_CLOCKS, ["clock_id", "tick_rate_num", "tick_rate_den"])
    ids = _plain(clocks.column("clock_id"))
    rows = clocks.filter(pc.equal(ids, pa.scalar(clock_id, ids.type))).to_pylist()
    if not rows:
        raise NotAligned(f"{CORE_CLOCKS} declares no {clock_id!r}, so its rate is unknown")
    num, den = rows[0]["tick_rate_num"], rows[0]["tick_rate_den"]
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
    found_tick = _session_value(packet, "t_zero_tick", session_id, NoTimeOrigin)
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


@overload
def attach_clocks(source: PacketLike | PacketSetLike, data: pa.Table, resource_id: str) -> pa.Table: ...
@overload
def attach_clocks(source: PacketLike | PacketSetLike, data: pa.RecordBatch, resource_id: str) -> pa.RecordBatch: ...
@overload
def attach_clocks(source: PacketLike | PacketSetLike, data: Stream, resource_id: str) -> pa.RecordBatchReader: ...
def attach_clocks(source: PacketLike | PacketSetLike, data: Arrow, resource_id: str) -> Arrow:
    """Add the clock each coordinate column's ticks are counted on, as the declaration says.

    A coordinate's clock is its `clock_from` target where declared, else the row's `clock_id`
    (Part 02 §8.4). A target in another table is read through the one reference this table
    declares to it, taking only that table's key and clock columns for the keys present. A row
    whose key finds no target row gets a null clock. :func:`clock_columns` names the added
    columns; one already in `table` is kept, so attaching twice is attaching once.

    Parameters
    ----------
    source : PacketLike or PacketSet
        The packet the rows came from, or the packet set, whose rows each go to the packet their
        `packet_key` names.
    data : pyarrow.Table, RecordBatch, RecordBatchReader, or pyarrow.dataset Scanner or Dataset
        Rows of `resource_id`. Only coordinates they carry get a clock, and each needs the
        columns its clock is reached through.
    resource_id : str
        The table's resource, whose declaration says where each clock is.

    Returns
    -------
    pyarrow.Table, RecordBatch or RecordBatchReader
        `data` with the clock columns appended: a Table or RecordBatch as its own type, anything
        else as a stream, which reads each referenced table once rather than per batch.

    Raises
    ------
    NotDeclared
        If `clock_from` names a table this one does not reference exactly once.
    ValueError
        If `table` lacks a column a clock is reached through.
    """
    if isinstance(source, PacketSetLike):
        return _over_sessions(
            source, data, lambda member, _, table, parents: _attach(member, resource_id, table, parents)
        )
    one = source
    parents: dict[str, pa.Table] | None = None if isinstance(data, (pa.Table, pa.RecordBatch)) else {}
    return _each(data, lambda table: _attach(one, resource_id, table, parents))


def _attach(packet: PacketLike, resource_id: str, table: pa.Table, parents: dict[str, pa.Table] | None) -> pa.Table:
    declared = _declared_table(packet, resource_id)
    named = clock_columns(packet, resource_id)
    for coordinate, source in _clock_sources(declared).items():
        if coordinate in table.column_names and named[coordinate] not in table.column_names:
            clock = _clock_of(packet, resource_id, declared, source, table, parents)
            table = table.append_column(named[coordinate], clock)
    return table


def _clock_of(
    packet: PacketLike,
    resource_id: str,
    declared: Mapping[str, Any],
    source: str,
    table: pa.Table,
    parents: dict[str, pa.Table] | None,
) -> Any:
    """Read the clock `source` names for each row of `table`, null where the hop finds no row.

    With `parents`, the referenced table is read whole once and kept there, for a stream whose
    batches would otherwise each read it.
    """
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
    columns = list(dict.fromkeys([*target_keys, target]))
    if parents is not None:
        if target_resource not in parents:
            parents[target_resource] = packet.table(target_resource, columns=columns)
        found = parents[target_resource]
    else:
        # Narrowed to the keys present: a parent such as `core.units` is small, but reading it
        # whole per call is what an accessor called per unit cannot afford.
        narrow: dict[str, Any] = {name: values(column) for name, column in zip(target_keys, local, strict=True)}
        found = packet.table(target_resource, columns=columns, **narrow)
    try:
        return lookup(local, found, target_keys, target)
    except ValueError:
        raise Refused(f"{target_resource} holds a key {resource_id} references more than once") from None


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
    if not ticks.null_count and not clock.null_count:
        # Nothing null, so nothing to gather around.
        parent, placed = _mapped(_pieces(ticks, clock), len(ticks), target, graph, bound)
        return _ticks(parent, placed, ticks.type), placed
    ticks, clock = _flat(ticks), _flat(clock)
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
            # A numpy fill is three times quicker than pa.repeat over hundreds of millions of rows.
            on_target = pa.array(np.full(table.num_rows, target, dtype=pa.array([], type=kind).to_numpy().dtype))
        # The column keeps its declared type; a dictionary of one value buys nothing on an integer.
        declared_type = table.schema.field(column).type
        table = table.set_column(table.column_names.index(column), column, on_target.cast(declared_type))
    return table if keep is None or keep.all() else table.filter(pa.array(keep))


@overload
def on_clock(
    source: PacketLike | PacketSetLike,
    data: pa.Table,
    clock: int | None = ...,
    *,
    resource_id: str | None = ...,
    bound: float | None = ...,
) -> pa.Table: ...
@overload
def on_clock(
    source: PacketLike | PacketSetLike,
    data: pa.RecordBatch,
    clock: int | None = ...,
    *,
    resource_id: str | None = ...,
    bound: float | None = ...,
) -> pa.RecordBatch: ...
@overload
def on_clock(
    source: PacketLike | PacketSetLike,
    data: Stream,
    clock: int | None = ...,
    *,
    resource_id: str | None = ...,
    bound: float | None = ...,
) -> pa.RecordBatchReader: ...
def on_clock(
    source: PacketLike | PacketSetLike,
    data: Arrow,
    clock: int | None = None,
    *,
    resource_id: str | None = None,
    bound: float | None = None,
) -> Arrow:
    """Return `data` with its ticks on one clock.

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
    source : PacketLike or PacketSet
        The packet the rows came from, for its anchors and its declared bound, or the packet set,
        whose rows each map in the packet their `packet_key` names; `clock` must then be unset
        or every packet's reference clock.
    data : pyarrow.Table, RecordBatch, RecordBatchReader, or pyarrow.dataset Scanner or Dataset
        Rows carrying `t_tick` and `clock_id`, or with `resource_id` rows of that resource. A
        stream is mapped batch by batch, so narrow it first: what comes back takes no pushdown.
    clock : int, optional
        The clock to map onto. Defaults to the packet's reference clock; where it declares none,
        to the one clock a table's rows reach, which a stream cannot know in advance and refuses.
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
    Refused
        If `source` is a packet set and `clock` is not every packet's reference clock, since a
        clock ID names a different clock in each packet.
    """
    if isinstance(source, PacketSetLike):
        return _over_sessions(
            source,
            data,
            lambda member, _, table, parents: _mapped_table(
                member,
                table,
                _stream_clock(member) if clock is None and parents is not None else shared_clock(member, clock),
                resource_id,
                bound,
                parents,
            ),
        )
    one = source
    parents: dict[str, pa.Table] | None = None
    if not isinstance(data, (pa.Table, pa.RecordBatch)):
        parents = {}
        if clock is None:
            clock = _stream_clock(one)
    return _each(data, lambda table: _mapped_table(one, table, clock, resource_id, bound, parents))


def _stream_clock(packet: PacketLike) -> int:
    """Return the clock a stream maps onto by default, which must be declared rather than found."""
    try:
        return reference_clock(packet)
    except NotAligned as undeclared:
        raise NotAligned(f"{undeclared}; name the clock, since a stream's clocks are not known in advance") from None


def _mapped_table(
    packet: PacketLike,
    table: pa.Table,
    clock: int | None,
    resource_id: str | None,
    bound: float | None,
    parents: dict[str, pa.Table] | None,
) -> pa.Table:
    if resource_id is None:
        # A bare table is one coordinate, `t_tick`, on its own `clock_id`.
        return _on_target(packet, table, {"clock_id": ["t_tick"]}, True, clock, bound)
    table = _attach(packet, resource_id, table, parents)
    declared = clock_columns(packet, resource_id)
    by_column: dict[str, list[str]] = {}
    for coordinate, column in declared.items():
        if coordinate in table.column_names:
            by_column.setdefault(column, []).append(coordinate)
    return _on_target(packet, table, by_column, len(declared) == 1, clock, bound)


@overload
def seconds(
    source: PacketLike | PacketSetLike, data: pa.Table, *, resource_id: str | None = ..., session_id: int | None = ...
) -> pa.Table: ...
@overload
def seconds(
    source: PacketLike | PacketSetLike,
    data: pa.RecordBatch,
    *,
    resource_id: str | None = ...,
    session_id: int | None = ...,
) -> pa.RecordBatch: ...
@overload
def seconds(
    source: PacketLike | PacketSetLike, data: Stream, *, resource_id: str | None = ..., session_id: int | None = ...
) -> pa.RecordBatchReader: ...
def seconds(
    source: PacketLike | PacketSetLike, data: Arrow, *, resource_id: str | None = None, session_id: int | None = None
) -> Arrow:
    """Add a `t_second` column to rows whose ticks are on the reference clock.

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
    source : PacketLike or PacketSet
        The packet the rows came from, for its origin and reference rate, or the packet set, whose
        rows each take the origin of the session their `packet_key` and `session_id` name.
    data : pyarrow.Table, RecordBatch, RecordBatchReader, or pyarrow.dataset Scanner or Dataset
        Rows carrying `t_tick` and `clock_id`, or with `resource_id` rows of that resource. Rows
        already known to be on the reference clock can stay a scan through
        :func:`seconds_expression` instead.
    resource_id : str, optional
        The resource the rows are of, whose declaration says which columns are coordinates.
    session_id : int, optional
        Which session's origin to use. Over a packet set each row's `packet_key` and `session_id`
        say, and naming one is an error.

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
    if isinstance(source, PacketSetLike):
        if session_id is not None:
            raise ValueError(
                "session_id names a session within one packet; over a packet set, "
                "each row says by its packet_key and session_id"
            )
        return _over_sessions(
            source,
            data,
            lambda member, session, table, parents: _seconds_of(member, session, table, resource_id, parents),
            by_session=True,
        )
    one = source
    parents: dict[str, pa.Table] | None = None if isinstance(data, (pa.Table, pa.RecordBatch)) else {}
    return _each(data, lambda table: _seconds_of(one, session_id, table, resource_id, parents))


def _seconds_of(
    packet: PacketLike,
    session_id: int | None,
    table: pa.Table,
    resource_id: str | None,
    parents: dict[str, pa.Table] | None,
) -> pa.Table:
    start, num, den = origin(packet, session_id)
    reference = reference_clock(packet, session_id=session_id)
    return _with_seconds(packet, table, resource_id, start, num / den, reference, parents)


def seconds_expression(packet: PacketLike, column: str = "t_tick", *, session_id: int | None = None) -> pc.Expression:
    """Return `column` in seconds as an expression, for ticks already on the reference clock.

    The arithmetic :func:`seconds` does, so a scan can project seconds without materializing.
    Nothing checks the clock: use it only where the rows are known to be on the reference clock.

    Examples
    --------
    >>> packet.scanner("analysis.spike_events", columns={"t_second": seconds_expression(packet)})  # doctest: +SKIP
    """
    start, num, den = origin(packet, session_id)
    offset = pc.subtract(pc.field(column), pa.scalar(start, pa.int64()))
    return pc.divide(offset.cast(pa.float64()), pa.scalar(float(num) / float(den)))


def _with_seconds(
    packet: PacketLike,
    table: pa.Table,
    resource_id: str | None,
    start: int,
    rate: float,
    reference: int,
    parents: dict[str, pa.Table] | None,
) -> pa.Table:
    if resource_id is None:
        pairs = {"t_tick": "clock_id"}
    else:
        table = _attach(packet, resource_id, table, parents)
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
        table = table.append_column(name, _seconds_column(table.column(coordinate), start, rate))
    return table


def _seconds_column(ticks: Any, start: int, rate: float) -> Any:
    """Return `(ticks - start) / rate` as float64, null where a tick is.

    A null-free column is computed in slices across threads: Arrow takes three single-threaded
    passes over one chunk, which on hundreds of millions of ticks costs more than mapping them.
    Each step is the same IEEE operation either way, so the seconds are identical.
    """
    if ticks.null_count or not pa.types.is_integer(ticks.type):
        offset = pc.subtract(ticks, pa.scalar(start, pa.int64()))
        return pc.divide(pc.cast(offset, pa.float64()), rate)
    out = np.empty(len(ticks), dtype=np.float64)
    pieces: list[tuple[int, NDArray[Any]]] = []
    offset = 0
    for chunk in ticks.chunks if isinstance(ticks, pa.ChunkedArray) else [ticks]:
        flat = chunk.to_numpy()
        pieces.extend((offset + lo, flat[lo : lo + _CHUNK_ROWS]) for lo in range(0, flat.size, _CHUNK_ROWS))
        offset += flat.size

    def run(piece: tuple[int, NDArray[Any]]) -> None:
        lo, flat = piece
        seconds = out[lo : lo + flat.size]
        seconds[:] = np.subtract(flat, start, dtype=np.int64)
        np.divide(seconds, rate, out=seconds)

    if len(pieces) > 1:
        with ThreadPoolExecutor(min(len(pieces), os.cpu_count() or 1)) as pool:
            list(pool.map(run, pieces))
    else:
        for piece in pieces:
            run(piece)
    return pa.array(out)


def shared_clock(packet: PacketLike, clock: int | None) -> int | None:
    """Return `clock` where it can be named across a packet set: unset, or `packet`'s reference clock.

    A clock ID is assigned within its packet, so any other names a different clock in each.

    Raises
    ------
    Refused
        If `clock` is set and is not the packet's declared reference clock.
    """
    if clock is None:
        return None
    try:
        reference = reference_clock(packet)
    except NotAligned:
        reference = None
    if clock != reference:
        raise Refused(
            f"clock {clock} names a different clock in each packet; over a packet set only the reference "
            "clock is shared, so leave clock unset"
        )
    return clock


def _over_sessions(
    members: PacketSetLike,
    data: Arrow,
    transform: Callable[[PacketLike, int | None, pa.Table, dict[str, pa.Table] | None], pa.Table],
    *,
    by_session: bool = False,
) -> Arrow:
    """Apply a per-packet transform to each packet's rows of a packet set, by their `packet_key`.

    With `by_session`, a packet holding several sessions has its rows split again by `session_id`,
    and the transform is given each one; otherwise it is given None. A stream keeps one cache of
    referenced tables per packet, so each is read once. Rows come back grouped by packet.
    """
    caches: dict[int, dict[str, pa.Table]] | None = None if isinstance(data, (pa.Table, pa.RecordBatch)) else {}

    def split(table: pa.Table) -> pa.Table:
        if "packet_key" not in table.column_names:
            raise ValueError("rows read from a packet set need packet_key to say which packet each came from")
        keys = table.column("packet_key")
        present = sorted(cast("list[int]", pc.unique(keys).drop_null().to_pylist()))
        if not present:
            # No row says which packet: the first packet maps nothing and gives the schema.
            present, table = [0], table.slice(0, 0)
        parts = []
        for key in present:
            packet = members._member(key)
            rows = table if len(present) == 1 else table.filter(pc.equal(keys, pa.scalar(key, keys.type)))
            parents = None if caches is None else caches.setdefault(key, {})
            for session_id, session_rows in _by_session(members._session_ids(key), rows, by_session):
                parts.append(transform(packet, session_id, session_rows, parents))
        return pa.concat_tables(parts, promote_options="permissive")

    return _each(data, split)


def _by_session(session_ids: list[int], rows: pa.Table, by_session: bool) -> list[tuple[int | None, pa.Table]]:
    """Split one packet's rows by `session_id` where the transform needs each session's own."""
    if not by_session:
        return [(None, rows)]
    if len(session_ids) == 1:
        return [(session_ids[0], rows)]
    if "session_id" not in rows.column_names:
        raise ValueError("rows of a packet holding several sessions need session_id to say which each is in")
    column = rows.column("session_id")
    present = sorted(cast("list[int]", pc.unique(column).drop_null().to_pylist())) or session_ids[:1]
    return [(s, rows.filter(pc.equal(column, pa.scalar(s, column.type)))) for s in present]


#: Rows a stream is gathered into before a transform runs: a Parquet batch is about 130,000 rows,
#: too few for the kernel's threads, and this many holds a few hundred MB.
_STREAM_ROWS = 1 << 22


def _coalesced(reader: pa.RecordBatchReader) -> Iterator[pa.Table]:
    """Yield `reader`'s batches gathered into tables of about :data:`_STREAM_ROWS` rows."""
    held: list[pa.RecordBatch] = []
    count = 0
    for batch in reader:
        held.append(batch)
        count += batch.num_rows
        if count >= _STREAM_ROWS:
            yield pa.Table.from_batches(held, schema=reader.schema)
            held, count = [], 0
    if held:
        yield pa.Table.from_batches(held, schema=reader.schema)


#: What a transform takes: one in memory, or a stream it maps batch by batch.
Stream = pa.RecordBatchReader | pads.Scanner | pads.Dataset
Arrow = pa.Table | pa.RecordBatch | Stream


def _each(data: Arrow, transform: Callable[[pa.Table], pa.Table]) -> Arrow:
    """Apply a table transform to any Arrow form, returning a Table or RecordBatch as itself and a stream otherwise."""
    if isinstance(data, pa.Table):
        return transform(data)
    if isinstance(data, pa.RecordBatch):
        out = transform(pa.Table.from_batches([data]))
        return pa.record_batch([column.combine_chunks() for column in out.columns], schema=out.schema)
    if isinstance(data, pads.Dataset):
        data = data.scanner()
    reader = data.to_reader() if isinstance(data, pads.Scanner) else data
    if not isinstance(reader, pa.RecordBatchReader):
        raise TypeError(
            f"expected a pyarrow Table, RecordBatch, RecordBatchReader, Scanner or Dataset, not {type(data)}"
        )
    tables = (transform(table) for table in _coalesced(reader))
    # The first batch fixes the schema; an empty stream takes it from an empty table.
    first = next(tables, None)
    if first is None:
        first = transform(reader.schema.empty_table())
    schema = first.schema

    def batches() -> Iterator[pa.RecordBatch]:
        yield from first.to_batches()
        for table in tables:
            yield from table.cast(schema).to_batches()

    return pa.RecordBatchReader.from_batches(schema, batches())


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
    "seconds_expression",
    "stored_intervals",
]
