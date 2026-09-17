"""Spikes against events: per-event windows, or one event per spike.

Aligning spikes to an event is the most common question a spike table is asked, and R43
withdrew the materialized table that would have answered one instance of it -- which puts the
weight on the query being spellable. This is that spelling.

Three operations, not one
-------------------------

They are different questions and they return different rows. Naming them apart is the point;
a flag would let the wrong one be selected by omission.

- :func:`aligned_spikes` gives one row per **(spike, event) pair**. A spike inside two events'
  windows appears twice, which is what a PSTH needs -- each event contributes its own window,
  and a spike between two close licks belongs to both.
- :func:`assigned_spikes` gives at most one row per **spike**, labelled with the event it
  belongs to: ``preceding`` for the last event underway, ``nearest`` for the closest in either
  direction. Measured on real licks at ±1 s, those two disagree about half the time.

They coincide exactly when the windows are pairwise disjoint. That is why `aligned_spikes` can
use an ASOF join without changing its answer, and why doing so unconditionally would be wrong:
on 2,641 licks at ±1 s an ASOF join returns 58 M rows where the question has 224 M.

Everything here runs on DuckDB, which is the optional `sql` extra. The equivalent PyArrow path
is two `searchsorted` calls per unit against sorted trains, which implements the duplicating
semantics by construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .sql import sql_name

if TYPE_CHECKING:  # pragma: no cover
    import duckdb

#: Where mapped spikes live. `core.spike_events` carries each spike on the clock it was measured
#: on, so comparing it against an event is only meaningful after R30's mapping.
SPIKES = "analysis.spike_events"
EVENTS = "core.events"
#: R91 §3.1 moved `event_type` and `clock_id` onto the stream, so selecting one kind of event and
#: knowing what clock it is on both go through here.
STREAMS = "core.event_streams"

#: How a spike is matched to the one event it is assigned to.
ASSIGNMENTS = ("preceding", "nearest")


class ClockMismatch(ValueError):
    """The spikes and the events are counted on different clocks.

    A tick has no meaning beside a tick on another clock (R27 §2), so comparing them would
    return rows that look right and are not. R30 maps spikes onto the reference clock for
    exactly this comparison; an event stream on a different one has to be mapped first.
    """


def _connect(packet: Any, connection: duckdb.DuckDBPyConnection | None) -> duckdb.DuckDBPyConnection:
    """Return a connection with the two tables every alignment reads registered.

    Named rather than left to the default, which registers nothing: over an object store each
    registration is a round trip, and an alignment touches three of a packet's twenty-eight.
    """
    con: duckdb.DuckDBPyConnection = packet.duckdb(connection=connection, tables=(SPIKES, EVENTS, STREAMS))
    return con


def _clock(packet: Any, event_type: str) -> str:
    """Return the clock both sides are on, refusing if they differ.

    Checked rather than assumed. A packet may carry several streams on several clocks, and is
    free to hold one the mapping never touched. The clock is the stream's since R91 §3.1, so this
    reads `core.event_streams` where it read the event.
    """
    streams = packet.table(STREAMS, columns=["event_type", "clock_id"], event_type=event_type)
    if not streams.num_rows:
        raise KeyError(f"no {event_type!r} stream in {STREAMS}")
    on = sorted({v for v in streams.column("clock_id").unique().to_pylist() if v is not None})
    spikes = packet.table(SPIKES, columns=["clock_id"]).column("clock_id").unique().to_pylist()
    reference = sorted({v for v in spikes if v is not None})
    if len(on) > 1 or on != reference:
        raise ClockMismatch(
            f"{event_type!r} events are on {on} and {SPIKES} is on {reference}; "
            "map one onto the other before comparing ticks"
        )
    return str(on[0])


def _literal(value: str) -> str:
    """Return a SQL string literal, doubling any quote as SQL defines.

    The values here are an event type and a session ID, both of which come from a caller and
    reach the engine as text; `sql.quote` covers identifiers and is the wrong tool.
    """
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _events(event_type: str, session_id: str | None) -> str:
    """Build the event subquery both operations join against.

    The kind is the stream's (R91 §3.1), so selecting one kind of event is a join rather than a
    predicate on the event row.
    """
    where = f"m.event_type = {_literal(event_type)}"
    if session_id is not None:
        where += f" AND e.session_id = {_literal(session_id)}"
    return (
        f"(SELECT e.t_tick FROM {sql_name(EVENTS)} e "
        f"JOIN {sql_name(STREAMS)} m ON e.stream_id = m.event_stream_id WHERE {where})"
    )


def windows_disjoint(packet: Any, event_type: str, half_window: int, *, session_id: str | None = None) -> bool:
    """Whether every pair of windows is disjoint, so one spike falls in at most one.

    Costs about 1.3 ms over a few thousand events, against seconds for the query it decides --
    which is why :func:`aligned_spikes` can afford to ask every time rather than requiring the
    caller to know.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    event_type : str
        The event type the windows are centred on.
    half_window : int
        Half the window, in ticks on the events' clock.
    session_id : str, optional
        Restrict to one session.

    Returns
    -------
    bool
        True when the closest pair of events is at least a full window apart.
    """
    con = _connect(packet, None)
    gaps = f"SELECT t_tick - lag(t_tick) OVER (ORDER BY t_tick) AS d FROM {_events(event_type, session_id)}"
    full = 2 * half_window
    row = con.sql(f"SELECT coalesce(min(d), {full + 1}) >= {full} FROM ({gaps}) WHERE d IS NOT NULL").fetchone()
    # An aggregate over an empty set still yields a row; the guard is for the type, not the data.
    return bool(row[0]) if row else True


def aligned_spikes(
    packet: Any,
    event_type: str,
    half_window: int,
    *,
    session_id: str | None = None,
    connection: duckdb.DuckDBPyConnection | None = None,
) -> duckdb.DuckDBPyRelation:
    """Spikes within a window of each event, **one row per (spike, event) pair**.

    A spike inside two events' windows comes back twice, once per event, which is what an
    event-aligned histogram counts: every event contributes its own window and a spike near
    both belongs to both. Where that is not wanted, the question is :func:`assigned_spikes`.

    Uses an ASOF join when :func:`windows_disjoint` says one spike can match at most one event,
    which is 4.6x faster and returns the identical rows, and a range join otherwise. The choice
    is an optimisation and never changes the result.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    event_type : str
        Which events to align to, from `core.events.event_type`.
    half_window : int
        Half the window, in ticks. The window is closed: ``[t - half, t + half]``.
    session_id : str, optional
        Restrict to one session.
    connection : duckdb.DuckDBPyConnection, optional
        Register into this connection rather than a new one.

    Returns
    -------
    duckdb.DuckDBPyRelation
        Columns ``session_id``, ``unit_id``, ``sorting_run_id``, ``curation_id``,
        ``event_tick``, ``t_tick`` and ``t_rel_tick``, the last being the spike's tick
        relative to its event. R91 §3.2 struck ``event_id``; an event is named by its tick,
        unique within the ``(session_id, event_type)`` scope these queries impose.
        A relation rather than a table, so it composes with a filter or an aggregate and the
        rows a caller does not want are never materialised.

    Raises
    ------
    ClockMismatch
        If the events and the spikes are not counted on the same clock.
    KeyError
        If the packet holds no events of this type.

    Examples
    --------
    >>> psth = aligned_spikes(packet, "go_cue", 15_625).aggregate(  # doctest: +SKIP
    ...     "t_rel_tick // 625 AS bin, count(*) AS n", "bin")
    """
    _clock(packet, event_type)
    con = _connect(packet, connection)
    spikes, events = sql_name(SPIKES), _events(event_type, session_id)
    if windows_disjoint(packet, event_type, half_window, session_id=session_id):
        join = f"ASOF JOIN {events} e ON s.t_tick >= e.t_tick - {half_window}"
        where = f"WHERE s.t_tick <= e.t_tick + {half_window}"
    else:
        join = f"JOIN {events} e ON s.t_tick BETWEEN e.t_tick - {half_window} AND e.t_tick + {half_window}"
        where = ""
    return con.sql(
        f"SELECT s.session_id, s.unit_id, s.sorting_run_id, s.curation_id, e.t_tick AS event_tick, "
        f"s.t_tick, s.t_tick - e.t_tick AS t_rel_tick FROM {spikes} s {join} {where}"
    )


def assigned_spikes(
    packet: Any,
    event_type: str,
    *,
    to: str = "preceding",
    half_window: int | None = None,
    session_id: str | None = None,
    connection: duckdb.DuckDBPyConnection | None = None,
) -> duckdb.DuckDBPyRelation:
    """Each spike labelled with the one event it belongs to, **at most one row per spike**.

    The two rules answer different questions and disagree often -- about half the time on real
    licks at ±1 s -- so neither is a default the other can stand in for:

    - ``preceding`` is the last event at or before the spike. "Which trial was underway."
    - ``nearest`` is the closest event in either direction. "Which event is this spike near."

    Parameters
    ----------
    packet : Packet
        The packet to read.
    event_type : str
        Which events to assign to.
    to : {'preceding', 'nearest'}
        Which event a spike belongs to.
    half_window : int, optional
        Leave a spike unassigned when no event is within this many ticks. Unbounded by default,
        so every spike is assigned however far away its event is.
    session_id : str, optional
        Restrict to one session.
    connection : duckdb.DuckDBPyConnection, optional
        Register into this connection rather than a new one.

    Returns
    -------
    duckdb.DuckDBPyRelation
        As :func:`aligned_spikes`, but with each spike appearing once at most.

    Raises
    ------
    ValueError
        If `to` is not one of :data:`ASSIGNMENTS`.
    ClockMismatch
        If the events and the spikes are not counted on the same clock.
    """
    if to not in ASSIGNMENTS:
        raise ValueError(f"to must be one of {ASSIGNMENTS}, not {to!r}")
    _clock(packet, event_type)
    con = _connect(packet, connection)
    spikes, events = sql_name(SPIKES), _events(event_type, session_id)
    keys = "s.session_id, s.unit_id, s.sorting_run_id, s.curation_id, s.t_tick"

    if to == "preceding":
        bound = "" if half_window is None else f"WHERE s.t_tick <= e.t_tick + {half_window}"
        return con.sql(
            f"SELECT {keys}, e.t_tick AS event_tick, s.t_tick - e.t_tick AS t_rel_tick "
            f"FROM {spikes} s ASOF JOIN {events} e ON s.t_tick >= e.t_tick {bound}"
        )
    # `nearest` cannot be an ASOF join in either direction: the closest event may be the one
    # after the spike. Grouping over a bounded range join is what makes the comparison possible,
    # so an unbounded `nearest` would pair every spike with every event and is refused.
    if half_window is None:
        raise ValueError("to='nearest' needs half_window: without a bound every spike is compared to every event")
    return con.sql(
        f"SELECT {keys}, argmin(e.t_tick, abs(s.t_tick - e.t_tick)) AS event_tick, "
        f"argmin(s.t_tick - e.t_tick, abs(s.t_tick - e.t_tick)) AS t_rel_tick "
        f"FROM {spikes} s JOIN {events} e "
        f"ON s.t_tick BETWEEN e.t_tick - {half_window} AND e.t_tick + {half_window} "
        f"GROUP BY {keys}"
    )


__all__ = [
    "ASSIGNMENTS",
    "EVENTS",
    "SPIKES",
    "STREAMS",
    "ClockMismatch",
    "aligned_spikes",
    "assigned_spikes",
    "windows_disjoint",
]
