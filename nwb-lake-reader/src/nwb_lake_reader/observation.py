"""When something was observing, which is what a rate is divided by (R38).

A point process is not a set of times. It is a set of times *and* the region over which
someone was looking, and without the second the first cannot be interpreted: a silent unit and
an unrecorded one produce the same rows, and two units observed for different spans produce
counts that must not be compared. R38 puts that region on the clock -- 13 rows for a session
where a per-unit table wanted 6,781 -- and lets a unit or a stream refine it where something
measured drift.

Resolving the inheritance is the work here. A unit's window is its own where it declares one
and its sorting run's clock's otherwise, and the two live in different tables, so a caller who
reads only one gets an answer that is wrong for whichever units the other covers.

Support is passed, not assumed
------------------------------

Nothing in this module defaults a denominator. :func:`rate` takes a count and a duration and
neither has a default, because the error this exists to prevent is arithmetic rather than
access: dividing by the wrong span, not failing to look one up. A packet that declares no
windows gets an empty table and no invented extent, as R39 §2.3 requires of an absent origin.

Ticks are inclusive
-------------------

`start_tick` and `stop_tick` are both observed (R18 §2, R38 §2.2), so a window covers
``stop - start + 1`` ticks. R38 §2.3 and §4 describe a probe clock's `stop_tick` as "the
recording's length", which reads as exclusive and disagrees with its own column definition by
one tick; the writer follows the column definition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.compute as pc

if TYPE_CHECKING:  # pragma: no cover
    import duckdb

CLOCK_INTERVALS = "core.clock_observation_intervals"
UNIT_INTERVALS = "core.unit_observation_intervals"
STREAM_INTERVALS = "core.event_stream_observation_intervals"

#: Where a resolved window came from. `declared` is the thing's own refinement, `inherited` is
#: its clock's. Kept because the two mean different things to a writer reading a finding back.
DECLARED = "declared"
INHERITED = "inherited"

_UNIT_KEY = ("session_id", "unit_id", "sorting_run_id", "curation_id")


def _has(packet: Any, resource_id: str) -> bool:
    """Whether the packet declares a resource. Every observation table is optional."""
    return resource_id in {r.resource_id for r in packet.resources()}


def _empty(names: tuple[str, ...]) -> pa.Table:
    """Build an empty result with the right columns, so a caller need not branch on absence."""
    fields = [
        pa.field(n, pa.int64() if n.endswith("_tick") else pa.string())
        for n in (*names, "clock_id", "start_tick", "stop_tick", "source")
    ]
    return pa.table({f.name: pa.array([], type=f.type) for f in fields})


def clock_windows(packet: Any, *, session_id: str | None = None, clock_id: str | None = None) -> pa.Table:
    """Return the intervals over which each clock was observing, in that clock's own ticks.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    session_id, clock_id : str, optional
        Restrict to one session or one clock.

    Returns
    -------
    pyarrow.Table
        Columns ``session_id``, ``clock_id``, ``start_tick`` and ``stop_tick``. Empty when the
        packet declares none, which is conforming: R9 §5 makes this optional.
    """
    if not _has(packet, CLOCK_INTERVALS):
        return pa.table(
            {
                n: pa.array([], type=pa.string() if n.endswith("id") else pa.int64())
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


def unit_windows(packet: Any, *, session_id: str | None = None) -> pa.Table:
    """Return each unit's observation windows, its own where declared and its clock's otherwise.

    A unit reaches its clock through its sorting run (R38 §2.5), which is why
    `core.sorting_runs.clock_id` exists: before it, a unit's clock was a naming convention no
    rule and no reader could follow.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    session_id : str, optional
        Restrict to one session.

    Returns
    -------
    pyarrow.Table
        The unit key, plus ``clock_id``, ``start_tick``, ``stop_tick`` and ``source``
        (:data:`DECLARED` or :data:`INHERITED`). One row per window, so a unit observed across
        a recording gap appears more than once.
    """
    if not _has(packet, "core.units") or not _has(packet, "core.sorting_runs"):
        return _empty(_UNIT_KEY)
    units = packet.table("core.units", columns=list(_UNIT_KEY), session_id=session_id)
    runs = {
        r["sorting_run_id"]: r["clock_id"]
        for r in packet.table("core.sorting_runs", columns=["sorting_run_id", "clock_id"]).to_pylist()
    }
    windows: dict[tuple[str | None, str | None], list[tuple[int, int]]] = {}
    for row in clock_windows(packet, session_id=session_id).to_pylist():
        windows.setdefault((row["session_id"], row["clock_id"]), []).append((row["start_tick"], row["stop_tick"]))

    rows = []
    for unit in units.to_pylist():
        clock = runs.get(unit["sorting_run_id"])
        for start, stop in windows.get((unit["session_id"], clock), []):
            rows.append({**unit, "clock_id": clock, "start_tick": start, "stop_tick": stop, "source": INHERITED})
    inherited = pa.Table.from_pylist(rows, schema=_empty(_UNIT_KEY).schema) if rows else _empty(_UNIT_KEY)

    own = _empty(_UNIT_KEY)
    if _has(packet, UNIT_INTERVALS):
        declared = packet.table(UNIT_INTERVALS, session_id=session_id).to_pylist()
        if declared:
            own = pa.Table.from_pylist(
                [
                    {
                        **{k: d[k] for k in _UNIT_KEY},
                        "clock_id": runs.get(d["sorting_run_id"]),
                        "start_tick": d["start_tick"],
                        "stop_tick": d["stop_tick"],
                        "source": DECLARED,
                    }
                    for d in declared
                ],
                schema=_empty(_UNIT_KEY).schema,
            )
    return _resolve(own, inherited, _UNIT_KEY)


def stream_windows(packet: Any, *, session_id: str | None = None) -> pa.Table:
    """Return each event stream's observation windows, declared or inherited from its clock.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    session_id : str, optional
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
    windows: dict[tuple[str | None, str | None], list[tuple[int, int]]] = {}
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
        "declared": (
            ("core_unit_observation_intervals", "core_sorting_runs"),
            """SELECT o.session_id, o.unit_id, o.sorting_run_id, o.curation_id, r.clock_id,
                      o.start_tick, o.stop_tick, 'declared' AS source
               FROM core_unit_observation_intervals o
               JOIN core_sorting_runs r ON o.sorting_run_id = r.sorting_run_id""",
        ),
        "inherited": (
            ("core_units", "core_sorting_runs", "core_clock_observation_intervals"),
            """SELECT u.session_id, u.unit_id, u.sorting_run_id, u.curation_id, r.clock_id,
                      c.start_tick, c.stop_tick, 'inherited' AS source
               FROM core_units u
               JOIN core_sorting_runs r
                 ON u.session_id = r.session_id AND u.sorting_run_id = r.sorting_run_id
               JOIN core_clock_observation_intervals c
                 ON c.session_id = r.session_id AND c.clock_id = r.clock_id
               {guard}""",
        ),
        "guard": """WHERE NOT EXISTS (
                   SELECT 1 FROM core_unit_observation_intervals o
                   WHERE o.session_id = u.session_id AND o.unit_id = u.unit_id
                     AND o.sorting_run_id = u.sorting_run_id AND o.curation_id = u.curation_id)""",
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


def register_views(connection: duckdb.DuckDBPyConnection) -> list[str]:
    """Register the observation views, using whichever branches the packet can bind.

    A view with no usable branch is skipped, so a packet carrying no observation tables offers
    no resolved window rather than an empty one that looks answered.

    Parameters
    ----------
    connection : duckdb.DuckDBPyConnection
        A connection with the packet's tables already registered.

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
    made = []
    for name, spec in VIEWS.items():
        refined = spec["refinements"] in known
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
    KeyError
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
            raise KeyError(f"clock {row['clock_id']!r} declares no tick rate, so its windows have no duration")
        total += (row["stop_tick"] - row["start_tick"] + 1) / hz
    return total


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
    "STREAM_INTERVALS",
    "UNIT_INTERVALS",
    "VIEWS",
    "clock_windows",
    "observed_seconds",
    "observed_ticks",
    "rate",
    "register_views",
    "stream_windows",
    "unit_windows",
]
