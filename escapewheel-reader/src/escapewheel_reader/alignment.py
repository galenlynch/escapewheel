"""Spikes against events, per event or per spike.

- :func:`aligned_spikes` -- one row per (spike, event) pair, as a PSTH needs.
- :func:`assigned_spikes` -- at most one row per spike, labelled with its preceding or nearest
  event.
- :func:`windows_disjoint` -- whether no spike falls in two windows, where the two agree.

Everything here runs on DuckDB, the optional `sql` extra.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .errors import ClockMismatch
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


def _connect(packet: Any, connection: duckdb.DuckDBPyConnection | None) -> duckdb.DuckDBPyConnection:
    """Return a connection with the two tables every alignment reads registered.

    Named rather than left to the default, which registers nothing: over an object store each
    registration is a round trip, and an alignment touches three of a packet's twenty-eight.
    """
    con: duckdb.DuckDBPyConnection = packet.duckdb(connection=connection, tables=(SPIKES, EVENTS, STREAMS))
    return con


def _clock(packet: Any, event_type: str, session_id: int | None) -> int:
    """Return the clock both sides are on, refusing if they differ.

    Checked rather than assumed. A packet may carry several streams on several clocks, and is
    free to hold one the mapping never touched. The clock is the stream's since R91 §3.1, so this
    reads `core.event_streams` where it read the event.
    """
    streams = packet.table(
        STREAMS,
        columns=["event_type", "clock_id"],
        event_type=event_type,
        session_id=session_id,
    )
    if not streams.num_rows:
        raise KeyError(f"no {event_type!r} stream in {STREAMS}")
    on = sorted({v for v in streams.column("clock_id").unique().to_pylist() if v is not None})
    spikes = packet.table(SPIKES, columns=["clock_id"], session_id=session_id).column("clock_id").unique().to_pylist()
    reference = sorted({v for v in spikes if v is not None})
    if len(on) > 1 or on != reference:
        raise ClockMismatch(
            f"{event_type!r} events are on {on} and {SPIKES} is on {reference}; "
            "map one onto the other before comparing ticks"
        )
    return int(on[0])


def _literal(value: str) -> str:
    """Return a SQL string literal, doubling any quote as SQL defines.

    The event type comes from a caller and reaches the engine as text; `sql.quote` covers
    identifiers and is the wrong tool.
    """
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _events(event_type: str, session_id: int | None) -> str:
    """Build the event subquery both operations join against.

    The kind is the stream's (R91 §3.1), so selecting one kind of event is a join rather than a
    predicate on the event row.
    """
    where = f"m.event_type = {_literal(event_type)}"
    if session_id is not None:
        where += f" AND e.session_id = {session_id}"
    return (
        f"(SELECT e.session_id, e.t_tick FROM {sql_name(EVENTS)} e "
        f"JOIN {sql_name(STREAMS)} m ON e.stream_id = m.event_stream_id WHERE {where})"
    )


def _spikes(session_id: int | None) -> str:
    """Build the spike relation with the same explicit session scope as the events."""
    table = sql_name(SPIKES)
    return table if session_id is None else f"(SELECT * FROM {table} WHERE session_id = {session_id})"


def windows_disjoint(packet: Any, event_type: str, half_window: int, *, session_id: int | None = None) -> bool:
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
    session_id : int, optional
        Restrict to one session.

    Returns
    -------
    bool
        True when the closest pair of events is at least a full window apart.
    """
    con = _connect(packet, None)
    gaps = (
        "SELECT t_tick - lag(t_tick) OVER (PARTITION BY session_id ORDER BY t_tick) AS d "
        f"FROM {_events(event_type, session_id)}"
    )
    full = 2 * half_window
    row = con.sql(f"SELECT coalesce(min(d), {full + 1}) >= {full} FROM ({gaps}) WHERE d IS NOT NULL").fetchone()
    # An aggregate over an empty set still yields a row; the guard is for the type, not the data.
    return bool(row[0]) if row else True


def aligned_spikes(
    packet: Any,
    event_type: str,
    half_window: int,
    *,
    session_id: int | None = None,
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
    session_id : int, optional
        Restrict to one session.
    connection : duckdb.DuckDBPyConnection, optional
        Register into this connection rather than a new one.

    Returns
    -------
    duckdb.DuckDBPyRelation
        Columns ``session_id``, ``unit_id``, ``event_tick``, ``t_tick`` and ``t_rel_tick``,
        the last being the spike's tick relative to its event. R91 §3.2 struck ``event_id``;
        an event is named by its tick,
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
    _clock(packet, event_type, session_id)
    con = _connect(packet, connection)
    spikes, events = _spikes(session_id), _events(event_type, session_id)
    if windows_disjoint(packet, event_type, half_window, session_id=session_id):
        join = f"ASOF JOIN {events} e ON s.session_id = e.session_id AND s.t_tick >= e.t_tick - {half_window}"
        where = f"WHERE s.t_tick <= e.t_tick + {half_window}"
    else:
        join = (
            f"JOIN {events} e ON s.session_id = e.session_id "
            f"AND s.t_tick BETWEEN e.t_tick - {half_window} AND e.t_tick + {half_window}"
        )
        where = ""
    return con.sql(
        f"SELECT s.session_id, s.unit_id, e.t_tick AS event_tick, "
        f"s.t_tick, s.t_tick - e.t_tick AS t_rel_tick FROM {spikes} s {join} {where}"
    )


def assigned_spikes(
    packet: Any,
    event_type: str,
    *,
    to: str = "preceding",
    half_window: int | None = None,
    session_id: int | None = None,
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
    session_id : int, optional
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
    _clock(packet, event_type, session_id)
    con = _connect(packet, connection)
    spikes, events = _spikes(session_id), _events(event_type, session_id)
    keys = "s.session_id, s.unit_id, s.t_tick"

    if to == "preceding":
        bound = "" if half_window is None else f"WHERE s.t_tick <= e.t_tick + {half_window}"
        return con.sql(
            f"SELECT {keys}, e.t_tick AS event_tick, s.t_tick - e.t_tick AS t_rel_tick "
            f"FROM {spikes} s ASOF JOIN {events} e "
            f"ON s.session_id = e.session_id AND s.t_tick >= e.t_tick {bound}"
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
        f"ON s.session_id = e.session_id "
        f"AND s.t_tick BETWEEN e.t_tick - {half_window} AND e.t_tick + {half_window} "
        f"GROUP BY {keys}"
    )


__all__ = [
    "ASSIGNMENTS",
    "EVENTS",
    "SPIKES",
    "STREAMS",
    "aligned_spikes",
    "assigned_spikes",
    "windows_disjoint",
]
