"""Row constraints as Arrow expressions, usable on any dataset or scanner.

- :func:`where` -- column constraints as one expression.
- :func:`tick_range` -- the rows whose coordinate lands in a range on a clock, as stored ticks.
- :func:`tick_bounds` -- the stored-tick intervals :func:`tick_range` tests, as a table.
- :data:`Predicate` -- what one constraint may be.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as pads
from numpy.typing import NDArray

from . import clocks
from .dictionaries import decoded
from .errors import NotAligned, NotDeclared
from .protocols import PacketLike, PacketSetLike

#: One column's constraint: a scalar is equality, a two-item tuple a closed range, a list or set
#: membership, and None no constraint.
Predicate = str | int | float | bool | tuple[Any, Any] | list[Any] | set[Any] | frozenset[Any] | None


def expression(constraints: Mapping[str, Predicate]) -> pads.Expression | None:
    """Build the expression for `constraints`, or None where they constrain nothing.

    An unknown column raises when the expression is applied, rather than silently matching nothing.
    Membership exists because several streams may carry one kind of event: resolving a type gives
    a set of keys, and pushing them down lets row-group statistics prune rather than reading and
    filtering.
    """
    found: pads.Expression | None = None
    for column, value in constraints.items():
        if value is None:
            continue
        field = pads.field(column)
        if isinstance(value, tuple):
            low, high = value
            term = (field >= low) & (field <= high)
        elif isinstance(value, (list, set, frozenset)):
            term = field.isin(list(value))
        else:
            term = field == value
        found = term if found is None else found & term
    return found


def where(**constraints: Predicate) -> pads.Expression:
    """Return column constraints as one expression, for a dataset's or scanner's `filter`.

    The same constraints :meth:`Packet.table` takes as keywords, on the values as stored.

    Examples
    --------
    >>> packet.scan("core.events").to_table(filter=where(stream_id=[1, 3], t_tick=(0, 30_000)))  # doctest: +SKIP
    """
    found = expression(constraints)
    return pc.scalar(True) if found is None else found


def tick_range(
    source: PacketLike | PacketSetLike,
    resource_id: str,
    span: tuple[int, int],
    *,
    clock: int | None = None,
    column: str | None = None,
) -> pads.Expression:
    """Return an expression matching the rows whose coordinate lands in `span` on `clock`, tested on stored ticks.

    Exact, so a scan filtered by it holds the rows :func:`~escapewheel_reader.clocks.on_clock`
    would keep in `span` and no others, and row-group statistics prune before anything is mapped.
    Each clock reaching `clock` contributes the stored intervals that land in `span` under the
    declared bound (:func:`~escapewheel_reader.clocks.stored_intervals`). A row on a clock that
    cannot reach `clock`, or whose anchors do not increase, is matched whatever its tick, so that
    mapping it refuses as it would without the range; a row on a null clock is never placed and
    never matched.

    Parameters
    ----------
    source : PacketLike or PacketSet
        The packet whose clocks and declarations the expression is built from. Over a packet set,
        each packet's expression is tested under its `packet_key`, since a clock ID is
        unique only within its packet, and `clock` must be unset or every packet's reference clock.
    resource_id : str
        The table the expression filters, whose declaration says where each coordinate's clock is.
    span : tuple of int
        The closed range, on `clock`.
    clock : int, optional
        The clock `span` is on. Defaults to the packet's reference clock.
    column : str, optional
        The coordinate to test. Required where the table declares more than one.

    Returns
    -------
    pyarrow.dataset.Expression
        For a table carrying its clock, an OR of `(clock_id == c) & (t_tick in [a, b])` per clock
        and interval; for one reaching its clock through a reference, as `core.spike_events` does
        through `core.units`, the clock test is on the referencing keys instead.

    Examples
    --------
    >>> packet.scanner("core.events", filter=tick_range(packet, "core.events", (lo, hi)))  # doctest: +SKIP
    """
    if isinstance(source, PacketSetLike):
        return _any(
            [
                pads.field("packet_key").isin([packet_key])
                & tick_range(member, resource_id, span, clock=clocks.shared_clock(member, clock), column=column)
                for member, packet_key in source._keyed(resource_id)
            ]
        )
    reach = _reach(source, resource_id, span, clock, column)
    ticks = pads.field(reach.coordinate)
    terms: list[pads.Expression] = []
    if reach.parent is None:
        clock_column = pads.field(reach.clock_from)
        for name, intervals in reach.intervals.items():
            if intervals[0].size:
                terms.append(clock_column.isin([name]) & _within(ticks, intervals))
        terms.append(pc.is_valid(clock_column) & pc.invert(clock_column.isin(list(reach.intervals))))
    else:
        clock_values = reach.parent.column(reach.clock_from)
        for name in reach.present:
            reached = reach.intervals.get(name)
            if reached is not None and not reached[0].size:
                continue
            rows = reach.parent.filter(pc.equal(clock_values, pa.scalar(name, clock_values.type)))
            keys = _keys_in(rows, reach.keys)
            terms.append(keys if reached is None else keys & _within(ticks, reached))
    return _any(terms) if terms else pc.scalar(False)


def tick_bounds(
    source: PacketLike | PacketSetLike,
    resource_id: str,
    span: tuple[int, int],
    *,
    clock: int | None = None,
    column: str | None = None,
) -> pa.Table:
    """Return the stored-tick intervals :func:`tick_range` tests, for a filter written in SQL or Polars.

    Takes :func:`tick_range`'s arguments. A clock with no interval landing in `span` has no row.

    Returns
    -------
    pyarrow.Table
        `clock_id`, `lo` and `hi`, int64, one row per closed interval: a stored tick on `clock_id`
        lands in `span` if and only if it lies in one of its clock's intervals. Over a packet set,
        `packet_key` first, since a clock ID is unique only within its packet.

    Raises
    ------
    NotAligned
        If the rows are on a clock that cannot reach `clock`, or whose anchors do not increase.
        :func:`tick_range` lets such rows through for mapping to refuse; a filter written from
        bounds has no mapping after it, so it would keep them as if they were in range.
    """
    if isinstance(source, PacketSetLike):
        parts = []
        for member, packet_key in source._keyed(resource_id):
            bounds = tick_bounds(member, resource_id, span, clock=clocks.shared_clock(member, clock), column=column)
            parts.append(bounds.add_column(0, "packet_key", pa.array([packet_key] * bounds.num_rows, pa.int32())))
        return pa.concat_tables(parts)
    reach = _reach(source, resource_id, span, clock, column)
    unplaced = [name for name in reach.present if name not in reach.intervals]
    if unplaced:
        raise NotAligned(
            f"rows of {resource_id} on clock(s) {unplaced} cannot be placed on the target clock, so no "
            "stored range selects them; exclude those clocks, or filter with tick_range and map with "
            "on_clock, which refuses them"
        )
    names: list[int] = []
    lows: list[int] = []
    highs: list[int] = []
    for name in reach.present:
        starts, stops = reach.intervals[name]
        names += [name] * starts.size
        lows += starts.tolist()
        highs += stops.tolist()
    return pa.table(
        {
            "clock_id": pa.array(names, pa.int64()),
            "lo": pa.array(lows, pa.int64()),
            "hi": pa.array(highs, pa.int64()),
        }
    )


@dataclass(frozen=True)
class _Reach:
    """What :func:`tick_range` and :func:`tick_bounds` test: per clock, the stored intervals in range.

    `intervals` holds each clock that reaches the target; a clock in `present` without an entry
    reaches it nowhere the mapping would accept, and its rows are left for the mapping to refuse.
    """

    coordinate: str
    clock_from: str
    present: list[int]
    intervals: dict[int, tuple[NDArray[np.int64], NDArray[np.int64]]]
    parent: pa.Table | None
    keys: list[tuple[str, str]]


def _reach(
    packet: PacketLike, resource_id: str, span: tuple[int, int], clock: int | None, column: str | None
) -> _Reach:
    declared = clocks._declared_table(packet, resource_id)
    sources = clocks._clock_sources(declared)
    if column is None:
        if len(sources) != 1:
            raise ValueError(f"{resource_id} declares coordinates {sorted(sources)}; name one as column")
        column = next(iter(sources))
    elif column not in sources:
        raise ValueError(f"{resource_id} declares no coordinate {column}; its coordinates are {sorted(sources)}")
    graph = clocks.clock_graph(packet)
    parent_resource, _, clock_from = sources[column].rpartition(".")
    parent: pa.Table | None = None
    keys: list[tuple[str, str]] = []
    if parent_resource:
        references = [r for r in declared.get("references", []) if r["resource"] == parent_resource]
        if len(references) != 1:
            raise NotDeclared(
                f"{resource_id} declares {len(references)} references to {parent_resource}, "
                f"so clock_from {sources[column]} names no single row"
            )
        keys = list(zip(references[0]["columns"], references[0]["resource_columns"], strict=True))
        names = list(dict.fromkeys([*(theirs for _, theirs in keys), clock_from]))
        parent = decoded(packet.table(parent_resource, columns=names))
        present = sorted(int(v) for v in pc.unique(parent.column(clock_from)).to_pylist() if v is not None)
    else:
        present = sorted(graph.clocks())
    target = clocks.default_clock(packet, present) if clock is None else int(clock)
    if not parent_resource:
        present = sorted({name for name in [*present, target] if target in graph.ancestry(name)})
    bound = clocks.declared_bound(packet)
    intervals = {}
    for name in present:
        if target not in graph.ancestry(name):
            continue
        try:
            intervals[name] = clocks.stored_intervals(graph, name, target, (int(span[0]), int(span[1])), bound)
        except (NotAligned, ValueError):  # Unanchored is a ValueError
            continue
    return _Reach(column, clock_from, present, intervals, parent, keys)


def _within(ticks: pads.Expression, intervals: tuple[NDArray[np.int64], NDArray[np.int64]]) -> pads.Expression:
    return _any([(ticks >= int(lo)) & (ticks <= int(hi)) for lo, hi in zip(*intervals, strict=True)])


def _keys_in(rows: pa.Table, keys: Sequence[tuple[str, str]]) -> pads.Expression:
    """Match exactly the key combinations `rows` holds, each key named here and in `rows`.

    A composite key is split on its key with the fewest values, so the expression stays exact
    without a term per combination.
    """
    ours, theirs = min(keys, key=lambda pair: len(pc.unique(rows.column(pair[1]))))
    found = pc.unique(rows.column(theirs)).drop_null()
    if len(keys) == 1:
        return pads.field(ours).isin(found)
    rest = [pair for pair in keys if pair != (ours, theirs)]
    values = rows.column(theirs)
    return _any([(pads.field(ours) == value) & _keys_in(rows.filter(pc.equal(values, value)), rest) for value in found])


def _any(terms: Sequence[pads.Expression]) -> pads.Expression:
    """OR `terms` as a balanced tree, whose depth stays logarithmic in their number."""
    if len(terms) == 1:
        return terms[0]
    middle = len(terms) // 2
    return _any(terms[:middle]) | _any(terms[middle:])


def on_clock_constraints(
    packet: PacketLike, resource_id: str, constraints: Mapping[str, Predicate], clock: int | None
) -> pads.Expression | None:
    """Build `constraints` with each one on a coordinate stated on `clock` rather than as stored.

    A scalar is the one-tick range and a list or set each of its ticks, so every form a stored
    constraint takes means the same on the clock.
    """
    coordinates = set(clocks.clock_columns(packet, resource_id))
    found = expression({name: value for name, value in constraints.items() if name not in coordinates})
    for name, value in constraints.items():
        if name not in coordinates or value is None:
            continue
        if isinstance(value, tuple):
            spans = [(int(value[0]), int(value[1]))]
        elif isinstance(value, (list, set, frozenset)):
            spans = [(int(v), int(v)) for v in value]
        else:
            spans = [(int(value), int(value))]
        terms = [tick_range(packet, resource_id, span, clock=clock, column=name) for span in spans]
        found = both(found, _any(terms) if terms else pc.scalar(False))
    return found


def both(first: pads.Expression | None, second: pads.Expression | None) -> pads.Expression | None:
    """AND two optional expressions."""
    if first is None or second is None:
        return second if first is None else first
    return first & second


__all__ = ["Predicate", "tick_bounds", "tick_range", "where"]
