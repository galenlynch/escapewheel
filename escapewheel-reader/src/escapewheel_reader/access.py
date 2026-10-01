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

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
import pyarrow.compute as pc

from . import clocks
from .errors import NotAligned, ResourceNotFoundError
from .observation import attach_support, unit_windows
from .runs import check as _check_runs

if TYPE_CHECKING:  # pragma: no cover
    from .packet import Packet

#: Ask for ticks exactly as the file stores them. Spikes are counted on the probe that
#: recorded them, so stored ticks from two probes are not comparable and neither is a stored
#: tick against a behavioural event -- which is why reaching them takes saying so.
STORED = "stored"

#: The activities whose runs produce units and spikes, so the accessors returning those know
#: what to check for currency (Part 01 §2.4). An accessor already names one resource; naming what
#: produces it is not the general activity-to-table map R44 §2.4 rejects, which an extension's
#: tables could never be added to.
SORTING_ACTIVITIES = ("spike_sorting", "curation")


def intervals(packet: Packet, *, session_id: int | None = None, interval_kind: str | None = None) -> pa.Table:
    """Read ``core.intervals``, optionally filtered (Part 01 §3.10).

    Filtering by kind prunes rather than scans: Part 02 §12.9 numbers each session's intervals
    of one kind consecutively, so each is a contiguous run in the file's order.

    Parameters
    ----------
    packet : Packet
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
    return packet.table("core.intervals", session_id=session_id, interval_kind=interval_kind)


def units(packet: Packet, *, session_id: int | None = None, quality_label: str | None = None) -> pa.Table:
    """Read ``core.units``, optionally filtered.

    Parameters
    ----------
    packet : Packet
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
        to read (Part 01 §2.4). Returning both concatenated is two complete sets of units with
        nothing marking the seam, so every count taken over the result is wrong. Read
        ``table("core.units")`` to get the rows anyway.
    """
    _check_runs(packet, SORTING_ACTIVITIES)
    return packet.table("core.units", session_id=session_id, quality_label=quality_label)


def events(
    packet: Packet,
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
    packet : Packet
        The packet to read.
    event_type : str, optional
        Keep only events of this type. The type is the stream's since R91 §3.1, so this
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
        Add a `t_second` column from the packet's declared origin (Part 01 §2.2). Refuses on
        a packet that declares none, and on ticks that are not on the reference clock.

    Returns
    -------
    pyarrow.Table
        Matching events, with `t_tick` on `clock` and `clock_id` naming it.
    """
    streams = None
    if event_type is not None:
        # R91 §3.1: one lookup in a table of streams, then a key filter on the events --
        # the shape R86 §2.4 measured as cheaper than carrying the type on every row.
        streams = (
            packet.table(
                "core.event_streams",
                columns=["event_stream_id"],
                event_type=event_type,
                session_id=session_id,
            )
            .column("event_stream_id")
            .to_pylist()
        )
    span = _span(packet, t_tick, clock)
    if streams is None:
        found = packet.table("core.events", session_id=session_id, t_tick=span)
    else:
        found = packet.table("core.events", session_id=session_id, t_tick=span, stream_id=streams)
    # A tick has no meaning without its clock, and R91 §3.2 puts the clock on the stream, so
    # the accessor attaches it: `core.event_streams` is tens of rows against an event table's
    # thousands, and every caller of this needs it either to convert or to report.
    stream_clocks = dict(
        zip(
            *(
                packet.table("core.event_streams", columns=["event_stream_id", "clock_id"]).column(c).to_pylist()
                for c in ("event_stream_id", "clock_id")
            ),
            strict=True,
        )
    )
    found = found.append_column(
        "clock_id", pa.array([stream_clocks.get(s) for s in found.column("stream_id").to_pylist()])
    )
    return _finish(packet, found, t_tick, clock, seconds, session_id)


def spike_times(
    packet: Packet,
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
    packet : Packet
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
        Add a `t_second` column from the packet's declared origin (Part 01 §2.2). Refuses on
        a packet that declares none, and on ticks that are not on the reference clock.

    Returns
    -------
    pyarrow.Table
        Columns ``t_tick`` and ``clock_id``, in stored order. When one `unit_id` is named
        and no `t_tick` range is given, the result carries the unit's observation window
        (R38) in `schema.metadata`, so :func:`~escapewheel_reader.observation.rate_of` needs
        no second lookup. A range-narrowed read carries none: the span is the caller's
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
        found = packet.table(
            "core.spike_events",
            columns=["t_tick"],
            unit_id=unit_id,
            session_id=session_id,
            t_tick=_span(packet, t_tick, clock),
        )
        unit_clocks = _unit_clocks(packet, ["unit_id"], unit_id=unit_id, session_id=session_id)
        found = found.append_column("clock_id", pa.array([unit_clocks.get((unit_id,))] * found.num_rows))
        found = _finish(packet, found, t_tick, clock, seconds, session_id)
        if t_tick is None:
            # Only for the unit's whole record. A range-narrowed read is a subset the
            # caller chose, and the window it was observed over is no denominator for it.
            found = attach_support(found, _unit_support(packet, unit_id, session_id))
        return found

    assert units is not None  # the exclusivity check above settles this
    keys = _reference_columns(packet, "core.spike_events", "core.units")
    missing = [k for k in keys if k not in units.schema.names]
    if missing:
        raise ValueError(f"units is missing {missing}, which identify a unit in this packet")
    # The values must match the type the scan produces. A caller may hand in a table
    # whose key columns are dictionary-encoded, and Arrow will not compare a dictionary
    # array against a plain column, so take the dictionary's values instead.
    tests = []
    for key in keys:
        values = units.column(key).unique()
        if pa.types.is_dictionary(values.type):
            values = values.cast(pa.string())
        tests.append(pc.field(key).isin(values))
    wanted = tests[0]
    for test in tests[1:]:
        wanted = wanted & test
    if session_id is not None:
        wanted = wanted & (pc.field("session_id") == session_id)
    if (pushed := _span(packet, t_tick, clock)) is not None:
        wanted = wanted & (pc.field("t_tick") >= pushed[0]) & (pc.field("t_tick") <= pushed[1])
    # R96 §3.4 struck `core.spike_events.clock_id`: a tick reaches its clock through its
    # unit now, so the column comes from the caller's `units` rather than from the scan.
    # A tick still travels with its clock, which is what this accessor exists to guarantee.
    found = packet.scan("core.spike_events").to_table(columns=["t_tick", *keys], filter=wanted)
    unit_clocks = _unit_clocks(packet, keys, session_id=session_id)
    found = found.append_column(
        "clock_id", pa.array([unit_clocks.get(tuple(r[k] for k in keys)) for r in found.select(keys).to_pylist()])
    )
    return _finish(packet, found.select(["t_tick", "clock_id"]), t_tick, clock, seconds, session_id)


def distinct(packet: Packet, resource_id: str, column: str) -> pa.ChunkedArray[Any]:
    """Return the distinct values of a column, from whichever table owns them.

    A foreign key means the parent table holds every value the child may carry, and it is
    the smaller table by construction -- `core.units` is thousands of rows where
    `core.spike_events` is hundreds of millions. So the answer comes from the parent, and
    the fact table is never scanned. Falls back to reading the column when no reference
    covers it, which is the honest thing rather than a wrong answer.

    Parameters
    ----------
    packet : Packet
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


def _references(packet: Packet, resource_id: str) -> list[dict[str, Any]]:
    """Return the references a table resource declares in the bound core registry."""
    declaration = (packet.registry or {}).get("resources", {}).get(resource_id, {})
    table = declaration.get("table", {}) if declaration.get("kind") == "table" else {}
    return list(table.get("references", []))


def _reference_columns(packet: Packet, resource_id: str, parent: str) -> list[str]:
    """Return the columns by which one resource references another, per the registry.

    Taking this from the registry keeps the accessor synchronized with the incorporated
    declaration instead of restating a relationship that can change independently.
    """
    for reference in _references(packet, resource_id):
        if reference["resource"] == parent:
            return list(reference["columns"])
    raise ResourceNotFoundError(f"the registry declares no reference from {resource_id} to {parent}")


def _unit_clocks(packet: Packet, keys: Sequence[str], **narrow: Any) -> dict[tuple[Any, ...], Any]:
    """Map a unit's key to the clock its ticks are counted on (R96 §3.2).

    The clock is the unit's fact, reached by a spike through the reference it already declares,
    and a tick still travels with its clock out of an accessor.
    """
    rows = packet.table("core.units", columns=[*keys, "clock_id"], **narrow).to_pylist()
    return {tuple(r[k] for k in keys): r["clock_id"] for r in rows}


def _unit_support(packet: Packet, unit_id: int, session_id: int | None) -> pa.Table:
    """Return one unit's observation windows, from the packet's resolved set (R38).

    The resolution is read once per packet and filtered here, because it reads three tables
    and this is called per unit.
    """
    windows = getattr(packet, "_support_cache", None)
    if windows is None:
        windows = unit_windows(packet)
        packet._support_cache = windows
    if not windows.num_rows:
        return windows
    unit_column = windows.column("unit_id")
    keep = pc.equal(unit_column, pa.scalar(unit_id, type=unit_column.type))
    if session_id is not None:
        session_column = windows.column("session_id")
        keep = pc.and_(keep, pc.equal(session_column, pa.scalar(session_id, type=session_column.type)))
    return windows.filter(keep)


def _span(
    packet: Packet, span: tuple[int, int] | None, clock: int | Literal["stored"] | None
) -> tuple[int, int] | None:
    """Widen a range stated on the result's clock into one the file can be pruned by."""
    if span is None or clock == STORED:
        return span
    try:
        target = clocks.reference_clock(packet) if clock is None else int(clock)
    except NotAligned:
        return span
    return clocks.stored_span(clocks.anchors(packet), target, span)


def _finish(
    packet: Packet,
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
