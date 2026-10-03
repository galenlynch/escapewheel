"""When something was observing, and rates over that span (Part 01 §2.3).

- :func:`unit_windows`, :func:`stream_windows`, :func:`clock_windows` -- when each unit, event
  stream or clock was observing, with inheritance resolved.
- :func:`observed_ticks`, :func:`observed_seconds` -- the total a set of windows covers.
- :func:`rate` -- a count divided by a duration, neither defaulted.
- :func:`rate_of` -- a table's rows divided by the support attached to it.
- :func:`attach_support`, :func:`support_of` -- set and read that support.
"""

from __future__ import annotations

import json

import pyarrow as pa
import pyarrow.compute as pc

from .dictionaries import decoded, join
from .errors import NotDeclared, StaleSupport
from .optional import held
from .protocols import PacketLike
from .resource_ids import (
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCKS,
    CORE_EVENT_STREAM_OBSERVATION_INTERVALS,
    CORE_EVENT_STREAMS,
    CORE_UNIT_OBSERVATION_INTERVALS,
    CORE_UNITS,
)

#: Where a resolved window came from. `declared` is the thing's own refinement, `inherited` is
#: its clock's. Kept because the two mean different things to a writer reading a finding back.
DECLARED = "declared"
INHERITED = "inherited"

#: What identifies a unit in a result. `unit_id` is the whole key (Part 02 §12.1); `session_id`
#: stays because every unit table carries it and a caller filters on it.
_UNIT_KEY = ("session_id", "unit_id")


def _empty(names: tuple[str, ...]) -> pa.Table:
    """Build an empty result with the right columns, so a caller need not branch on absence.

    Types follow the roles the registry assigns: a `_tick` is a coordinate in int64, an `_id`
    an identifier in int32 (Part 02 §5.3), and what remains is a label. Pinning them all to one
    type makes the empty result unable to concatenate with a populated one.
    """

    def _type(name: str) -> pa.DataType:
        if name.endswith("_tick"):
            return pa.int64()
        return pa.int32() if name.endswith("_id") else pa.string()

    fields = [pa.field(n, _type(n)) for n in (*names, "clock_id", "start_tick", "stop_tick", "source")]
    return pa.table({f.name: pa.array([], type=f.type) for f in fields})


def clock_windows(packet: PacketLike, *, session_id: int | None = None, clock_id: int | None = None) -> pa.Table:
    """Return the intervals over which each clock was observing, in that clock's own ticks.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.
    session_id, clock_id : int, optional
        Restrict to one session or one clock.

    Returns
    -------
    pyarrow.Table
        Columns ``session_id``, ``clock_id``, ``start_tick`` and ``stop_tick``. Empty when the
        packet declares none, which Part 02 §12.5 forbids; no extent is invented for it.
    """
    if CORE_CLOCK_OBSERVATION_INTERVALS not in held(packet):
        return pa.table(
            {
                n: pa.array([], type=pa.int32() if n.endswith("id") else pa.int64())
                for n in ("session_id", "clock_id", "start_tick", "stop_tick")
            }
        )
    columns = ["session_id", "clock_id", "start_tick", "stop_tick"]
    table: pa.Table = packet.table(
        CORE_CLOCK_OBSERVATION_INTERVALS, columns=columns, session_id=session_id, clock_id=clock_id
    )
    return table


def _resolve(own: pa.Table, inherited: pa.Table, key: tuple[str, ...]) -> pa.Table:
    """Combine declared windows with inherited ones, dropping an inheritance that is refined.

    Refinement replaces rather than adds. A thing that declares any window of its own declares
    all of them, so keeping the clock's alongside would widen the very span the refinement
    narrowed -- which is the arithmetic this module exists to get right.
    """
    if not own.num_rows:
        return inherited
    if not inherited.num_rows:
        return own
    refined = own.select(list(key)).group_by(list(key)).aggregate([])
    kept = join(inherited, refined, list(key), "left anti")
    return pa.concat_tables([own, kept.select(own.column_names)])


def _windows(table: pa.Table, source: str, key: tuple[str, ...]) -> pa.Table:
    """Shape joined rows into the result schema, every row from `source`."""
    schema = _empty(key).schema
    table = table.append_column("source", pa.repeat(pa.scalar(source), table.num_rows))
    return table.select(schema.names).cast(schema)


def unit_windows(packet: PacketLike, *, session_id: int | None = None) -> pa.Table:
    """Return each unit's observation windows, its own where declared and its clock's otherwise.

    A unit declares the clock on which its ticks are counted. Observation support belongs to
    the session carrying that unit, so inherited windows match both the session and the clock.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.
    session_id : int, optional
        Restrict to one session.

    Returns
    -------
    pyarrow.Table
        The unit key, plus ``clock_id``, ``start_tick``, ``stop_tick`` and ``source``
        (:data:`DECLARED` or :data:`INHERITED`). One row per window, so a unit observed across
        a recording gap appears more than once.
    """
    if CORE_UNITS not in held(packet):
        return _empty(_UNIT_KEY)
    units = packet.table(CORE_UNITS, columns=[*_UNIT_KEY, "clock_id"], session_id=session_id)
    clocks = clock_windows(packet, session_id=session_id)
    inherited = _windows(join(units, clocks, ["session_id", "clock_id"]), INHERITED, _UNIT_KEY)

    own = _empty(_UNIT_KEY)
    if CORE_UNIT_OBSERVATION_INTERVALS in held(packet):
        # The interval row names only the unit, and its clock is the unit's.
        declared = decoded(
            packet.table(
                CORE_UNIT_OBSERVATION_INTERVALS, columns=[*_UNIT_KEY, "start_tick", "stop_tick"], session_id=session_id
            )
        )
        clock_of = units.select(["unit_id", "clock_id"])
        own = _windows(join(declared, clock_of, ["unit_id"], "left outer"), DECLARED, _UNIT_KEY)
    return _resolve(own, inherited, _UNIT_KEY)


def stream_windows(packet: PacketLike, *, session_id: int | None = None) -> pa.Table:
    """Return each event stream's observation windows, declared or inherited from its clock.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.
    session_id : int, optional
        Restrict to one session.

    Returns
    -------
    pyarrow.Table
        Columns ``event_stream_id``, ``clock_id``, ``start_tick``, ``stop_tick`` and
        ``source``.
    """
    key = ("event_stream_id",)
    if CORE_EVENT_STREAMS not in held(packet):
        return _empty(key)
    streams = decoded(
        packet.table(CORE_EVENT_STREAMS, columns=["event_stream_id", "session_id", "clock_id"], session_id=session_id)
    )
    clocks = clock_windows(packet, session_id=session_id)
    inherited = _windows(join(streams, clocks, ["session_id", "clock_id"]), INHERITED, key)

    own = _empty(key)
    if CORE_EVENT_STREAM_OBSERVATION_INTERVALS in held(packet):
        # Inner, so a window of a stream outside the selected session is left out.
        declared = decoded(
            packet.table(
                CORE_EVENT_STREAM_OBSERVATION_INTERVALS, columns=["event_stream_id", "start_tick", "stop_tick"]
            )
        )
        clock_of = streams.select(["event_stream_id", "clock_id"])
        own = _windows(join(declared, clock_of, ["event_stream_id"]), DECLARED, key)
    return _resolve(own, inherited, key)


def observed_ticks(windows: pa.Table) -> int:
    """Return the total ticks the windows cover.

    Both ends are observed, so a window of one tick has ``start == stop`` and covers 1, not 0.
    Windows within one thing must not overlap -- the registry checks it -- so this sums rather
    than unions, and a caller passing windows from several units gets their total and not their
    span.

    Parameters
    ----------
    windows : pyarrow.Table
        Rows carrying ``start_tick`` and ``stop_tick``.

    Returns
    -------
    int
        Ticks observed.
    """
    if not windows.num_rows:
        return 0
    spans = pc.add(pc.subtract(windows.column("stop_tick"), windows.column("start_tick")), 1)
    return int(pc.sum(spans).as_py())


def observed_seconds(packet: PacketLike, windows: pa.Table) -> float:
    """Return the seconds the windows cover, using each clock's declared rate.

    Parameters
    ----------
    packet : PacketLike
        The packet the windows came from.
    windows : pyarrow.Table
        Rows carrying ``clock_id``, ``start_tick`` and ``stop_tick``.

    Returns
    -------
    float
        Seconds observed.

    Raises
    ------
    NotDeclared
        If a window names a clock the packet does not declare, or one with no rate. Refused
        rather than skipped: a missing rate would silently shorten the denominator.
    """
    if not windows.num_rows:
        return 0.0
    clocks = decoded(packet.table(CORE_CLOCKS, columns=["clock_id", "tick_rate_hz", "tick_rate_num", "tick_rate_den"]))
    num, den = (pc.cast(clocks.column(c), pa.float64()) for c in ("tick_rate_num", "tick_rate_den"))
    # The exact ratio where both terms are given and nonzero, the decimal rate otherwise.
    zero = pa.scalar(0.0)
    exact = pc.fill_null(pc.and_(pc.not_equal(num, zero), pc.not_equal(den, zero)), pa.scalar(False))
    hz = pc.if_else(exact, pc.divide(num, den), pc.cast(clocks.column("tick_rate_hz"), pa.float64()))
    rates = pa.table({"clock_id": clocks.column("clock_id"), "hz": hz})
    timed = join(windows.select(["clock_id", "start_tick", "stop_tick"]), rates, ["clock_id"], "left outer")
    hz_of = timed.column("hz")
    undeclared = timed.filter(pc.or_kleene(pc.is_null(hz_of), pc.equal(hz_of, zero)))
    if undeclared.num_rows:
        clock = undeclared.column("clock_id")[0].as_py()
        raise NotDeclared(f"clock {clock!r} declares no tick rate, so its windows have no duration")
    ticks = pc.add(pc.subtract(timed.column("stop_tick"), timed.column("start_tick")), 1)
    return float(pc.sum(pc.divide(pc.cast(ticks, pa.float64()), timed.column("hz"))).as_py())


#: Schema-metadata keys carrying an attached support and the row count it describes.
SUPPORT_KEY = b"escapewheel.support"
ROWS_KEY = b"escapewheel.support_rows"


def attach_support(table: pa.Table, windows: pa.Table) -> pa.Table:
    """Return `table` carrying `windows` as its support, fingerprinted by row count.

    For one point process. Attaching windows that differ between the rows would make
    :func:`rate_of` average over denominators that are not interchangeable, so an accessor
    returning several units attaches nothing and leaves the caller to group and look up.

    Parameters
    ----------
    table : pyarrow.Table
        The rows the support describes.
    windows : pyarrow.Table
        Windows from :func:`unit_windows` or :func:`stream_windows`.

    Returns
    -------
    pyarrow.Table
        The same rows, with the support in `schema.metadata`. Unchanged when `windows` is empty,
        so an absent support is absent rather than empty.
    """
    if not windows.num_rows:
        return table
    carried = windows.select(["clock_id", "start_tick", "stop_tick"]).to_pylist()
    metadata = dict(table.schema.metadata or {})
    metadata[SUPPORT_KEY] = json.dumps(carried).encode()
    metadata[ROWS_KEY] = str(table.num_rows).encode()
    return table.replace_schema_metadata(metadata)


def support_of(table: pa.Table) -> pa.Table | None:
    """Return the support attached to `table`, or None if it carries none.

    Parameters
    ----------
    table : pyarrow.Table
        A table from an accessor that attaches support.

    Returns
    -------
    pyarrow.Table or None
        Columns ``clock_id``, ``start_tick`` and ``stop_tick``.

    Raises
    ------
    StaleSupport
        If the row count has changed since the support was attached.
    """
    metadata = table.schema.metadata or {}
    if SUPPORT_KEY not in metadata:
        return None
    expected = int(metadata[ROWS_KEY])
    if table.num_rows != expected:
        raise StaleSupport(
            f"support was attached for {expected} rows and this table has {table.num_rows}; "
            "read it again rather than adjusting the denominator"
        )
    rows = json.loads(metadata[SUPPORT_KEY])
    return pa.table(
        {
            # No type pinned: the support is rebuilt from what was recorded, so the column
            # takes the values' own type.
            "clock_id": pa.array([r["clock_id"] for r in rows]),
            "start_tick": pa.array([r["start_tick"] for r in rows], type=pa.int64()),
            "stop_tick": pa.array([r["stop_tick"] for r in rows], type=pa.int64()),
        }
    )


def rate_of(packet: PacketLike, table: pa.Table) -> float:
    """Return the rate of a table's rows over the support attached to it.

    Parameters
    ----------
    packet : PacketLike
        The packet the table came from, for its clocks' rates.
    table : pyarrow.Table
        Rows from an accessor that attaches support.

    Returns
    -------
    float
        Rows per second.

    Raises
    ------
    NotDeclared
        If the table carries no support. Nothing is guessed: the caller resolves the windows
        with :func:`unit_windows` and divides with :func:`rate`.
    StaleSupport
        If the rows have changed since the support was attached.
    """
    windows = support_of(table)
    if windows is None:
        raise NotDeclared(
            "this table carries no support, so its rate has no denominator; "
            "resolve one with unit_windows or stream_windows and use rate()"
        )
    return rate(table.num_rows, observed_seconds(packet, windows))


def rate(count: int, seconds: float) -> float:
    """Return events per second.

    Both arguments are required. The measured error this guards against was arithmetic and not
    lookup -- a rate taken over a span the thing was not observed for -- so a default here would
    reintroduce exactly the mistake.

    Parameters
    ----------
    count : int
        How many events.
    seconds : float
        How long the thing was observed, from :func:`observed_seconds`.

    Returns
    -------
    float
        Events per second.

    Raises
    ------
    ValueError
        If `seconds` is not positive. A count over no observation is not zero, it is undefined.
    """
    if seconds <= 0:
        raise ValueError("a rate over an unobserved span is undefined, not zero")
    return count / seconds


__all__ = [
    "clock_windows",
    "observed_seconds",
    "observed_ticks",
    "rate",
    "rate_of",
    "stream_windows",
    "support_of",
    "unit_windows",
]
