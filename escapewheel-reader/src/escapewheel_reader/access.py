"""A packet's commonest reads, each returning a table.

- :func:`intervals` -- ``core.intervals`` by session and kind.
- :func:`units` -- ``core.units``, refusing where two sortings coexist with no preference.
- :func:`events` -- ``core.events`` by type, on the reference clock.
- :func:`spike_times` -- one unit's spikes or a table of units', on the reference clock.
- :func:`distinct` -- a column's distinct values, read from the smaller table that owns them.
- :data:`STORED` -- asks :func:`events` or :func:`spike_times` for ticks as stored.

Ticks come back on the packet's reference clock with `clock_id` alongside, because stored ticks
from two clocks are not comparable.
"""

from __future__ import annotations

from typing import Any, Literal

import pyarrow as pa
import pyarrow.compute as pc

from . import clocks
from .dictionaries import key_filter, within
from .errors import NotAligned, NotDeclared
from .observation import attach_support, unit_windows
from .predicates import both, expression, tick_range
from .protocols import Memo, PacketLike
from .resource_ids import CORE_EVENT_STREAMS, CORE_EVENTS, CORE_INTERVALS, CORE_SPIKE_EVENTS, CORE_UNITS
from .resources import read_pool
from .runs import check as _check_runs

#: Ask for ticks exactly as the file stores them. Spikes are counted on the probe that
#: recorded them, so stored ticks from two probes are not comparable and neither is a stored
#: tick against a behavioural event -- which is why reaching them takes saying so.
STORED = "stored"

#: The activities whose runs produce units and spikes, so the accessors returning those know
#: what to check for currency. An accessor already names one resource, so naming what produces
#: it is no general map from an activity to its tables, which an extension's tables could never
#: be added to.
SORTING_ACTIVITIES = ("spike_sorting", "curation")


def intervals(packet: PacketLike, *, session_id: int | None = None, interval_kind: str | None = None) -> pa.Table:
    """Read ``core.intervals``, optionally filtered.

    Filtering by kind prunes rather than scans: Part 02 §12.9 numbers each session's intervals
    of one kind consecutively, so each is a contiguous run in the file's order.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.
    session_id : int, optional
        Keep only this session.
    interval_kind : str, optional
        Keep only intervals of this kind, named as a dotted resource ID.

    Returns
    -------
    pyarrow.Table
        Matching intervals.
    """
    return packet.table(CORE_INTERVALS, session_id=session_id, interval_kind=interval_kind)


def units(packet: PacketLike, *, session_id: int | None = None, quality_label: str | None = None) -> pa.Table:
    """Read ``core.units``, optionally filtered.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.
    session_id : int, optional
        Keep only this session.
    quality_label : str, optional
        Keep only units with this curation label: ``sua``, ``mua``, or ``noise``.

    Returns
    -------
    pyarrow.Table
        Matching units.

    Raises
    ------
    AmbiguousRun
        If the packet holds two sortings or curations of one probe and does not say which
        to read (Part 01 §2.6). Returning both concatenated is two complete sets of units with
        nothing marking the seam, so every count taken over the result is wrong. Read
        ``table("core.units")`` to get the rows anyway.
    """
    _check_runs(packet, SORTING_ACTIVITIES)
    return packet.table(CORE_UNITS, session_id=session_id, quality_label=quality_label)


def events(
    packet: PacketLike,
    *,
    event_type: str | None = None,
    session_id: int | None = None,
    t_tick: tuple[int, int] | None = None,
    clock: int | Literal["stored"] | None = None,
    seconds: bool = False,
) -> pa.Table:
    """Read ``core.events``, on the packet's reference clock unless told otherwise.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.
    event_type : str, optional
        Keep only events of this type. The type is the stream's (Part 01 §3.11), so this
        resolves the streams that emit it and keeps their events. The vocabulary is open,
        so an unrecognized value is not an error, only empty.
    session_id : int, optional
        Keep only this session.
    t_tick : tuple of int, optional
        Keep only events within this closed tick range, stated on the clock the result
        comes back on -- so a range and the ticks it selects are always in the same space.
        A loose translation of it is pushed into the Parquet reader for pruning and the
        exact one applied after mapping.
    clock : int or 'stored', optional
        The clock to return ticks on. Defaults to :func:`~escapewheel_reader.clocks.reference_clock`;
        pass :data:`STORED` for the ticks the file holds.
    seconds : bool, default False
        Add a `t_second` column from the packet's declared origin. Refuses on
        a packet that declares none, and on ticks that are not on the reference clock.

    Returns
    -------
    pyarrow.Table
        Matching events, with `t_tick` on `clock` and `clock_id` naming it.
    """
    streams = None
    if event_type is not None:
        # One lookup in a table of streams, then a key filter on the events --
        # the shape R86 §2.4 measured as cheaper than carrying the type on every row.
        streams = (
            packet.table(
                CORE_EVENT_STREAMS,
                columns=["event_stream_id"],
                event_type=event_type,
                session_id=session_id,
            )
            .column("event_stream_id")
            .to_pylist()
        )
    wanted = both(
        expression({"session_id": session_id, "stream_id": streams}), _range(packet, CORE_EVENTS, t_tick, clock)
    )
    found = packet.scan(CORE_EVENTS).to_table(filter=wanted, memory_pool=read_pool())
    # A tick has no meaning without its clock, and every caller needs it either to convert or to
    # report, so the stream's clock comes back with each event.
    found = clocks.attach_clocks(packet, found, CORE_EVENTS)
    return _finish(packet, found, t_tick, clock, seconds, session_id)


def spike_times(
    packet: PacketLike,
    unit_id: int | None = None,
    *,
    units: pa.Table | None = None,
    session_id: int | None = None,
    t_tick: tuple[int, int] | None = None,
    clock: int | Literal["stored"] | None = None,
    seconds: bool = False,
) -> pa.Table:
    """Read spike times for one unit, or for a table of them.

    **On the reference clock by default.** A spike is counted on the probe that recorded
    it, so stored ticks from two probes are not comparable and neither is a stored tick
    against a behavioural event; returning them by default makes the wrong answer the
    easy one. `clock_id` comes back alongside `t_tick` either way, because a tick has no
    meaning without the clock it was counted on.

    A unit is identified within a packet by ``unit_id`` alone. ``session_id`` scopes the
    rows searched but never contributes to the unit's identity. An exact ``unit_id`` or an
    explicit table of units is already an unambiguous selection, so this accessor does not
    apply the current-run chooser used by :func:`units`.

    It is also the fast path. `core.units` is thousands of rows and `core.spike_events` is
    hundreds of millions, so resolving which units are wanted in the small table and
    pushing their keys into the large one is the shape this format is built for: the keys
    are compared against row-group statistics, and groups that cannot match are never
    read. The alternative -- reading the identity columns back out of the spike table to
    work out which rows are wanted -- scans hundreds of millions of rows to answer a
    question thousands of rows already answer.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.
    unit_id : int, optional
        One unit. Mutually exclusive with `units`.
    units : pyarrow.Table, optional
        Units to read, as returned by :func:`units` and filtered however the caller
        likes. Only its key columns are used; any others are ignored.
    session_id : int, optional
        Restrict every session-scoped input used by the read to this session.
    t_tick : tuple of int, optional
        Keep only spikes within this closed tick range, stated on the clock the result
        comes back on, not on the unit's stored clock -- a range and the ticks it selects
        are always in the same space. Pass `clock=STORED` for both in stored ticks.
    clock : int or 'stored', optional
        The clock to return ticks on. Defaults to :func:`~escapewheel_reader.clocks.reference_clock`;
        pass :data:`STORED` for the ticks the file holds. Mapping drops a spike the anchors
        cannot place, exactly as `analysis.spike_events` does.
    seconds : bool, default False
        Add a `t_second` column from the packet's declared origin. Refuses on
        a packet that declares none, and on ticks that are not on the reference clock.

    Returns
    -------
    pyarrow.Table
        The columns identifying the unit, then ``t_tick`` and ``clock_id``, in stored order,
        so a read of several units can be grouped by unit. When one `unit_id` is named and
        no `t_tick` range is given, the result carries the unit's observation window in
        `schema.metadata`, so :func:`~escapewheel_reader.observation.rate_of` needs no
        second lookup. A range-narrowed read carries none: the span is the caller's
        choice and is no denominator for it.

    Raises
    ------
    ValueError
        If both or neither of `unit_id` and `units` are given.

    Examples
    --------
    >>> spike_times(packet, units=units(packet, quality_label="sua"))  # doctest: +SKIP
    """
    if (unit_id is None) == (units is None):
        raise ValueError("name exactly one of unit_id or units")
    if unit_id is not None:
        wanted = both(
            expression({"unit_id": unit_id, "session_id": session_id}), _range(packet, CORE_SPIKE_EVENTS, t_tick, clock)
        )
        found = packet.scan(CORE_SPIKE_EVENTS).to_table(
            columns=["t_tick", "unit_id"], filter=wanted, memory_pool=read_pool()
        )
        found = clocks.attach_clocks(packet, found, CORE_SPIKE_EVENTS).select(["unit_id", "t_tick", "clock_id"])
        found = _finish(packet, found, t_tick, clock, seconds, session_id)
        if t_tick is None:
            # Only for the unit's whole record. A range-narrowed read is a subset the
            # caller chose, and the window it was observed over is no denominator for it.
            found = attach_support(found, _unit_support(packet, unit_id, session_id))
        return found

    assert units is not None  # the exclusivity check above settles this
    keys = _reference_columns(packet, CORE_SPIKE_EVENTS, CORE_UNITS)
    missing = [k for k in keys if k not in units.schema.names]
    if missing:
        raise ValueError(f"units is missing {missing}, which identify a unit in this packet")
    wanted, exact = key_filter(units, keys)
    if session_id is not None:
        wanted = wanted & (pc.field("session_id") == session_id)
    if (pushed := _range(packet, CORE_SPIKE_EVENTS, t_tick, clock)) is not None:
        wanted = wanted & pushed
    found = packet.scan(CORE_SPIKE_EVENTS).to_table(columns=["t_tick", *keys], filter=wanted, memory_pool=read_pool())
    if not exact:
        found = within(found, units, keys)
    found = clocks.attach_clocks(packet, found, CORE_SPIKE_EVENTS)
    return _finish(packet, found.select([*keys, "t_tick", "clock_id"]), t_tick, clock, seconds, session_id)


def distinct(packet: PacketLike, resource_id: str, column: str) -> pa.ChunkedArray[Any]:
    """Return the distinct values of a column, from whichever table owns them.

    A foreign key means the parent table holds every value the child may carry, and it is
    the smaller table by construction -- `core.units` is thousands of rows where
    `core.spike_events` is hundreds of millions. So the answer comes from the parent, and
    the fact table is never scanned. Falls back to reading the column when no reference
    covers it, which is the honest thing rather than a wrong answer.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.
    resource_id : str
        Dotted resource ID.
    column : str
        The column whose values are wanted.

    Returns
    -------
    pyarrow.Array
        The distinct values, unordered.
    """
    present = {r.resource_id for r in packet.resources()}
    for reference in _references(packet, resource_id):
        if column not in reference["columns"] or reference["resource"] not in present:
            continue
        parent_column = reference["resource_columns"][reference["columns"].index(column)]
        return packet.table(reference["resource"], columns=[parent_column]).column(0).unique()
    return packet.table(resource_id, columns=[column]).column(0).unique()


def _references(packet: PacketLike, resource_id: str) -> list[dict[str, Any]]:
    """Return the references a table resource declares in the bound core registry."""
    declaration = (packet.registry or {}).get("resources", {}).get(resource_id, {})
    table = declaration.get("table", {}) if declaration.get("kind") == "table" else {}
    return list(table.get("references", []))


def _reference_columns(packet: PacketLike, resource_id: str, parent: str) -> list[str]:
    """Return the columns by which one resource references another, per the registry.

    Taking this from the registry keeps the accessor synchronized with the incorporated
    declaration instead of restating a relationship that can change independently.
    """
    for reference in _references(packet, resource_id):
        if reference["resource"] == parent:
            return list(reference["columns"])
    raise NotDeclared(f"the registry declares no reference from {resource_id} to {parent}")


def _unit_support(packet: PacketLike, unit_id: int, session_id: int | None) -> pa.Table:
    """Return one unit's observation windows, from the packet's resolved set.

    The resolution is read once into the packet's memo and filtered here, because it reads
    three tables and this is called per unit.
    """
    memo = Memo.of(packet)
    if memo.unit_windows is None:
        memo.unit_windows = unit_windows(packet)
    windows = memo.unit_windows
    if not windows.num_rows:
        return windows
    unit_column = windows.column("unit_id")
    keep = pc.equal(unit_column, pa.scalar(unit_id, type=unit_column.type))
    if session_id is not None:
        session_column = windows.column("session_id")
        keep = pc.and_(keep, pc.equal(session_column, pa.scalar(session_id, type=session_column.type)))
    return windows.filter(keep)


def _range(
    packet: PacketLike, resource_id: str, span: tuple[int, int] | None, clock: int | Literal["stored"] | None
) -> pc.Expression | None:
    """Turn a range stated on the result's clock into a filter on the ticks the file holds."""
    if span is None:
        return None
    if clock == STORED:
        return expression({"t_tick": span})
    try:
        return tick_range(packet, resource_id, span, clock=None if clock is None else int(clock))
    except NotAligned:
        return None  # no clock to state it on; mapping refuses or decides, and the cut follows it


def _finish(
    packet: PacketLike,
    table: pa.Table,
    span: tuple[int, int] | None,
    clock: int | Literal["stored"] | None,
    seconds: bool,
    session_id: int | None,
) -> pa.Table:
    """Map ticks onto the requested clock, apply the caller's range exactly, and add seconds."""
    if clock != STORED:
        table = _narrowed(clocks.on_clock(packet, table, None if clock is None else int(clock)), span)
    return clocks.seconds(packet, table, session_id=session_id) if seconds else table


def _narrowed(table: pa.Table, span: tuple[int, int] | None) -> pa.Table:
    """Apply the caller's range exactly, now that every row is on one clock."""
    if span is None:
        return table
    ticks = table.column("t_tick")
    lower = pa.scalar(span[0], type=ticks.type)
    upper = pa.scalar(span[1], type=ticks.type)
    return table.filter(pc.and_(pc.greater_equal(ticks, lower), pc.less_equal(ticks, upper)))


__all__ = ["STORED", "distinct", "events", "intervals", "spike_times", "units"]
