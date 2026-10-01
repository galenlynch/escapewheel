"""When something was observing, and rates over that span (Part 01 §2.3).

- :func:`unit_windows`, :func:`stream_windows`, :func:`clock_windows` -- when each unit, event
  stream or clock was observing, with inheritance resolved.
- :func:`observed_ticks`, :func:`observed_seconds` -- the total a set of windows covers.
- :func:`rate` -- a count divided by a duration, neither defaulted.
- :func:`rate_of` -- a table's rows divided by the support attached to it.
- :func:`attach_support`, :func:`support_of` -- set and read that support.
- :func:`register_views` -- `unit_observation` and `stream_observation` as DuckDB views.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.compute as pc

from .errors import NotDeclared, StaleSupport

if TYPE_CHECKING:  # pragma: no cover
    import duckdb

CLOCK_INTERVALS = "core.clock_observation_intervals"
UNIT_INTERVALS = "core.unit_observation_intervals"
STREAM_INTERVALS = "core.event_stream_observation_intervals"

#: Where a resolved window came from. `declared` is the thing's own refinement, `inherited` is
#: its clock's. Kept because the two mean different things to a writer reading a finding back.
DECLARED = "declared"
INHERITED = "inherited"

#: What identifies a unit in a result. R81 §2.1 made `unit_id` the whole key; `session_id`
#: stays because every unit table carries it and a caller filters on it.
_UNIT_KEY = ("session_id", "unit_id")


def _has(packet: Any, resource_id: str) -> bool:
    """Whether the packet declares a resource. Every observation table is optional."""
    return resource_id in {r.resource_id for r in packet.resources()}


def _empty(names: tuple[str, ...]) -> pa.Table:
    """Build an empty result with the right columns, so a caller need not branch on absence.

    Types follow R48's roles as the registry assigns them: a `_tick` is a coordinate in int64,
    an `_id` an identifier in int32 (R53 §2.1), and what remains is a label. Pinning them all to
    one type makes the empty result unable to concatenate with a populated one.
    """

    def _type(name: str) -> pa.DataType:
        if name.endswith("_tick"):
            return pa.int64()
        return pa.int32() if name.endswith("_id") else pa.string()

    fields = [pa.field(n, _type(n)) for n in (*names, "clock_id", "start_tick", "stop_tick", "source")]
    return pa.table({f.name: pa.array([], type=f.type) for f in fields})


def clock_windows(packet: Any, *, session_id: int | None = None, clock_id: int | None = None) -> pa.Table:
    """Return the intervals over which each clock was observing, in that clock's own ticks.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    session_id, clock_id : int, optional
        Restrict to one session or one clock.

    Returns
    -------
    pyarrow.Table
        Columns ``session_id``, ``clock_id``, ``start_tick`` and ``stop_tick``. Empty when the
        packet declares none, which Part 02 §12.5 forbids; no extent is invented for it.
    """
    if not _has(packet, CLOCK_INTERVALS):
        return pa.table(
            {
                n: pa.array([], type=pa.int32() if n.endswith("id") else pa.int64())
                for n in ("session_id", "clock_id", "start_tick", "stop_tick")
            }
        )
    columns = ["session_id", "clock_id", "start_tick", "stop_tick"]
    table: pa.Table = packet.table(CLOCK_INTERVALS, columns=columns, session_id=session_id, clock_id=clock_id)
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
    refined = {tuple(row[k] for k in key) for row in own.to_pylist()}
    keep = [i for i, row in enumerate(inherited.to_pylist()) if tuple(row[k] for k in key) not in refined]
    return pa.concat_tables([own, inherited.take(pa.array(keep, type=pa.int64()))])


def unit_windows(packet: Any, *, session_id: int | None = None) -> pa.Table:
    """Return each unit's observation windows, its own where declared and its clock's otherwise.

    A unit declares the clock on which its ticks are counted. Observation support belongs to
    the session carrying that unit, so inherited windows match both the session and the clock.

    Parameters
    ----------
    packet : Packet
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
    # R96 §3.2 moved the clock from the run to the unit, so the run is no longer read here: a
    # unit names the clock its ticks are counted on, and the map through `core.sorting_runs`
    # this used to build was answering that question one table away.
    if not _has(packet, "core.units"):
        return _empty(_UNIT_KEY)
    units = packet.table("core.units", columns=[*_UNIT_KEY, "clock_id"], session_id=session_id)
    windows: dict[tuple[int | None, int | None], list[tuple[int, int]]] = {}
    for row in clock_windows(packet, session_id=session_id).to_pylist():
        windows.setdefault((row["session_id"], row["clock_id"]), []).append((row["start_tick"], row["stop_tick"]))

    rows = []
    for unit in units.to_pylist():
        clock = unit["clock_id"]
        keyed = {k: unit[k] for k in _UNIT_KEY}
        for start, stop in windows.get((unit["session_id"], clock), []):
            rows.append({**keyed, "clock_id": clock, "start_tick": start, "stop_tick": stop, "source": INHERITED})
    inherited = pa.Table.from_pylist(rows, schema=_empty(_UNIT_KEY).schema) if rows else _empty(_UNIT_KEY)

    own = _empty(_UNIT_KEY)
    if _has(packet, UNIT_INTERVALS):
        # R81 §2.3 leaves the interval row naming only the unit, and R96 §3.2 puts the clock on
        # the unit, so one lookup answers what two did.
        by_unit = {u["unit_id"]: u["clock_id"] for u in units.to_pylist()}
        declared = packet.table(UNIT_INTERVALS, session_id=session_id).to_pylist()
        if declared:
            own = pa.Table.from_pylist(
                [
                    {
                        **{k: d[k] for k in _UNIT_KEY},
                        "clock_id": by_unit.get(d["unit_id"]),
                        "start_tick": d["start_tick"],
                        "stop_tick": d["stop_tick"],
                        "source": DECLARED,
                    }
                    for d in declared
                ],
                schema=_empty(_UNIT_KEY).schema,
            )
    return _resolve(own, inherited, _UNIT_KEY)


def stream_windows(packet: Any, *, session_id: int | None = None) -> pa.Table:
    """Return each event stream's observation windows, declared or inherited from its clock.

    Parameters
    ----------
    packet : Packet
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
    if not _has(packet, "core.event_streams"):
        return _empty(key)
    streams = packet.table(
        "core.event_streams", columns=["event_stream_id", "session_id", "clock_id"], session_id=session_id
    ).to_pylist()
    windows: dict[tuple[int | None, int | None], list[tuple[int, int]]] = {}
    for row in clock_windows(packet, session_id=session_id).to_pylist():
        windows.setdefault((row["session_id"], row["clock_id"]), []).append((row["start_tick"], row["stop_tick"]))

    rows = [
        {
            "event_stream_id": s["event_stream_id"],
            "clock_id": s["clock_id"],
            "start_tick": start,
            "stop_tick": stop,
            "source": INHERITED,
        }
        for s in streams
        for start, stop in windows.get((s["session_id"], s["clock_id"]), [])
    ]
    inherited = pa.Table.from_pylist(rows, schema=_empty(key).schema) if rows else _empty(key)

    own = _empty(key)
    if _has(packet, STREAM_INTERVALS):
        clock_of = {s["event_stream_id"]: s["clock_id"] for s in streams}
        declared = [d for d in packet.table(STREAM_INTERVALS).to_pylist() if d["event_stream_id"] in clock_of]
        if declared:
            own = pa.Table.from_pylist(
                [
                    {
                        "event_stream_id": d["event_stream_id"],
                        "clock_id": clock_of[d["event_stream_id"]],
                        "start_tick": d["start_tick"],
                        "stop_tick": d["stop_tick"],
                        "source": DECLARED,
                    }
                    for d in declared
                ],
                schema=_empty(key).schema,
            )
    return _resolve(own, inherited, key)


#: How the SQL path resolves R38's inheritance, as ``{view: spec}``.
#:
#: A packet that needs no refinement does not carry the table to refine with -- units inherit
#: their clock's window in the common case, so `core.unit_observation_intervals` is absent --
#: and DuckDB binds a view at creation rather than deferring. So the view is assembled from the
#: parts that can bind: the declaring branch is dropped when its table is absent, and the
#: inheriting branch's `NOT EXISTS` guard is dropped with it, being vacuously true.
#:
#: This restates the CTEs inside the registry's two `within_observation` rules rather than
#: sharing code with them, and the duplication is deliberate: a rule must be runnable by any
#: implementation from `logical_schemas.json` alone (R2 §7.4), so it cannot depend on a view
#: this reader happens to register. `tests/test_observation.py` asserts the two agree on the
#: same packet, which is drift protection without the coupling.
VIEWS: dict[str, dict[str, Any]] = {
    "unit_observation": {
        "refinements": "core_unit_observation_intervals",
        # R96 §3.2 put the clock on the unit, so neither arm reaches through `core.sorting_runs`.
        "declared": (
            ("core_unit_observation_intervals", "core_units"),
            """SELECT o.session_id, o.unit_id, u.clock_id,
                      o.start_tick, o.stop_tick, 'declared' AS source
               FROM core_unit_observation_intervals o
               JOIN core_units u ON o.unit_id = u.unit_id""",
        ),
        "inherited": (
            ("core_units", "core_clock_observation_intervals"),
            """SELECT u.session_id, u.unit_id, u.clock_id,
                      c.start_tick, c.stop_tick, 'inherited' AS source
               FROM core_units u
               JOIN core_clock_observation_intervals c
                 ON c.session_id = u.session_id AND c.clock_id = u.clock_id
               {guard}""",
        ),
        "guard": """WHERE NOT EXISTS (
                   SELECT 1 FROM core_unit_observation_intervals o
                   WHERE o.unit_id = u.unit_id)""",
    },
    "stream_observation": {
        "refinements": "core_event_stream_observation_intervals",
        "declared": (
            ("core_event_stream_observation_intervals", "core_event_streams"),
            """SELECT o.event_stream_id, s.clock_id, o.start_tick, o.stop_tick, 'declared' AS source
               FROM core_event_stream_observation_intervals o
               JOIN core_event_streams s ON o.event_stream_id = s.event_stream_id""",
        ),
        "inherited": (
            ("core_event_streams", "core_clock_observation_intervals"),
            """SELECT s.event_stream_id, s.clock_id, c.start_tick, c.stop_tick, 'inherited' AS source
               FROM core_event_streams s
               JOIN core_clock_observation_intervals c
                 ON c.session_id = s.session_id AND c.clock_id = s.clock_id
               {guard}""",
        ),
        "guard": """WHERE NOT EXISTS (
                   SELECT 1 FROM core_event_stream_observation_intervals o
                   WHERE o.event_stream_id = s.event_stream_id)""",
    },
}


def register_views(connection: duckdb.DuckDBPyConnection, declared: Collection[str] | None = None) -> list[str]:
    """Register the observation views, using whichever branches the packet can bind.

    A view with no usable branch is skipped, so a packet carrying no observation tables offers
    no resolved window rather than an empty one that looks answered.

    `declared` is what the **packet** holds, against which `connection` holds whatever has been
    registered so far. The two differ once registration is by demand rather than wholesale, and
    conflating them is a silent wrong answer: a refinements table that exists but is not yet
    registered makes `refined` false, which drops the guard and returns an inherited window for
    every unit that has a declared one. So a view whose refinements table the packet holds and
    the connection lacks is skipped rather than built, and gets built when that table arrives.

    Parameters
    ----------
    connection : duckdb.DuckDBPyConnection
        A connection with some of the packet's tables registered.
    declared : collection of str, optional
        SQL names of every table the packet declares. Defaults to what is registered, which is
        correct only when everything has been.

    Returns
    -------
    list of str
        The views created, in registration order.
    """
    known = {
        row[0]
        for row in connection.sql(
            "SELECT table_name FROM duckdb_tables() UNION SELECT view_name FROM duckdb_views()"
        ).fetchall()
    }
    held = known if declared is None else set(declared)
    made = []
    for name, spec in VIEWS.items():
        refinements = spec["refinements"]
        if refinements in held and refinements not in known:
            continue
        refined = refinements in known
        branches = []
        needs, sql = spec["declared"]
        if known.issuperset(needs):
            branches.append(sql)
        needs, sql = spec["inherited"]
        if known.issuperset(needs):
            branches.append(sql.format(guard=spec["guard"] if refined else ""))
        if not branches:
            continue
        connection.sql(f"CREATE OR REPLACE VIEW {name} AS " + " UNION ALL ".join(branches))
        made.append(name)
    return made


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


def observed_seconds(packet: Any, windows: pa.Table) -> float:
    """Return the seconds the windows cover, using each clock's declared rate.

    Parameters
    ----------
    packet : Packet
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
    rates = {}
    for clock in packet.table(
        "core.clocks", columns=["clock_id", "tick_rate_hz", "tick_rate_num", "tick_rate_den"]
    ).to_pylist():
        if clock["tick_rate_num"] and clock["tick_rate_den"]:
            rates[clock["clock_id"]] = clock["tick_rate_num"] / clock["tick_rate_den"]
        elif clock["tick_rate_hz"]:
            rates[clock["clock_id"]] = float(clock["tick_rate_hz"])
    total = 0.0
    for row in windows.to_pylist():
        hz = rates.get(row["clock_id"])
        if not hz:
            raise NotDeclared(f"clock {row['clock_id']!r} declares no tick rate, so its windows have no duration")
        total += (row["stop_tick"] - row["start_tick"] + 1) / hz
    return total


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
    carried = [
        {"clock_id": r["clock_id"], "start_tick": r["start_tick"], "stop_tick": r["stop_tick"]}
        for r in windows.to_pylist()
    ]
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
            # No type pinned: a clock_id is an int32 identifier (R53 §2.1) and the support is
            # rebuilt from what was recorded, so the column takes the values' own type.
            "clock_id": pa.array([r["clock_id"] for r in rows]),
            "start_tick": pa.array([r["start_tick"] for r in rows], type=pa.int64()),
            "stop_tick": pa.array([r["stop_tick"] for r in rows], type=pa.int64()),
        }
    )


def rate_of(packet: Any, table: pa.Table) -> float:
    """Return the rate of a table's rows over the support attached to it.

    Parameters
    ----------
    packet : Packet
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
    "CLOCK_INTERVALS",
    "DECLARED",
    "INHERITED",
    "ROWS_KEY",
    "STREAM_INTERVALS",
    "SUPPORT_KEY",
    "UNIT_INTERVALS",
    "VIEWS",
    "attach_support",
    "clock_windows",
    "observed_seconds",
    "observed_ticks",
    "rate",
    "rate_of",
    "register_views",
    "stream_windows",
    "support_of",
    "unit_windows",
]
