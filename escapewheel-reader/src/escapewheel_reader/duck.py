"""One packet's tables in DuckDB.

- :func:`registered` -- a connection with the tables a caller asks for registered as views.
- :func:`register` -- register named tables on a connection, then the observation views.
- :func:`named_in` -- the declared tables a query mentions.
- :func:`register_views`, :data:`VIEWS` -- `unit_observation` and `stream_observation` as views.
- :func:`connect` -- an in-memory connection, or why SQL is unavailable.
- :func:`prepare_remote` -- set a connection up to read from an object store.

DuckDB is the optional ``sql`` extra. Only :func:`connect` imports it, so importing this module
does not.
"""

from __future__ import annotations

import contextlib
import re
import warnings
from collections.abc import Collection, Sequence
from typing import TYPE_CHECKING, Any, Literal

from .errors import ResourceUnreadableError
from .resources import TableResource
from .sql import sql_name

if TYPE_CHECKING:  # pragma: no cover
    import duckdb

    from .location import Location
    from .manifest import Resource

#: What :func:`connect` says of a packet where DuckDB is absent.
READS_WITHOUT_SQL = (
    "It is optional because a complete read path exists without it: table(), the accessors, and "
    "TableResource.dataset() all go through PyArrow."
)


def connect(reads_without: str) -> duckdb.DuckDBPyConnection:
    """Open an in-memory connection, or refuse naming the extra and what reads without it."""
    try:
        import duckdb as _duckdb
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(f"SQL access requires duckdb; install the 'sql' extra. {reads_without}") from exc
    return _duckdb.connect()


def prepare_remote(connection: duckdb.DuckDBPyConnection) -> None:
    """Set up a connection that will read from an object store.

    Two settings, and getting either wrong fails quietly. `httpfs` is what lets DuckDB open an
    `s3://` URI at all. `enable_object_cache` keeps Parquet footers across queries and is worth
    16x on a repeated read -- 3.38 s against 0.21 s over one session's spikes -- with no error
    and no signal when it is off, which is the kind of wrong this package exists to prevent.

    Credentials are deliberately **not** set. Whether a store is reachable is a property of the
    caller's situation rather than of the packet, so a caller supplies its own secret;
    what this removes is the setup a caller cannot be expected to know.
    """
    with contextlib.suppress(Exception):  # an older duckdb, or an extension it cannot fetch
        connection.execute("INSTALL httpfs")
        connection.execute("LOAD httpfs")
    with contextlib.suppress(Exception):
        connection.execute("SET enable_object_cache=true")


def registered(
    root: Location,
    declared: Sequence[Resource],
    *,
    connection: duckdb.DuckDBPyConnection | None,
    tables: Collection[str] | Literal["all"] | None,
    for_query: str | None,
) -> duckdb.DuckDBPyConnection:
    """Register the table resources a caller asks for and return the connection.

    The body of :meth:`escapewheel_reader.Packet.duckdb`, which documents the arguments; `root`
    and `declared` are the packet's root and its table resources.
    """
    con = connection if connection is not None else connect(READS_WITHOUT_SQL)
    if any(not TableResource(r, root).is_local for r in declared):
        prepare_remote(con)
    wanted = {r.resource_id for r in declared} if tables == "all" else set(tables or ())
    if for_query is not None:
        wanted |= named_in(for_query, declared)
    register(con, root, declared, wanted)
    return con


def register(
    connection: duckdb.DuckDBPyConnection, root: Location, declared: Sequence[Resource], wanted: Collection[str]
) -> None:
    """Register the named tables that are not on this connection already, then the views.

    Asking the connection what it holds rather than remembering keeps this correct when a
    caller registers something itself, and costs one local query against a round trip per
    table saved.
    """
    if not wanted:
        return
    # `internal` excludes DuckDB's own catalog views, which are numerous and none of ours.
    held = {row[0] for row in connection.sql("SELECT view_name FROM duckdb_views() WHERE NOT internal").fetchall()}
    skipped = []
    for resource in declared:
        if resource.resource_id not in wanted or sql_name(resource.resource_id) in held:
            continue
        try:
            TableResource(resource, root).register(connection)
        except ResourceUnreadableError as exc:
            # Not silently: an unregistered view fails later as "table does not exist",
            # which points at the query rather than at the resource that could not be read.
            skipped.append(f"{resource.resource_id} ({exc})")
    if skipped:
        listed = "\n  ".join(skipped)
        warnings.warn(
            f"{len(skipped)} table(s) could not be registered and are absent from this connection:\n  {listed}",
            # Attributed to `Packet.duckdb`, two frames up through `registered`.
            stacklevel=3,
        )
    # After the tables, because DuckDB binds a view at creation and one over a table this
    # packet does not declare is refused rather than deferred. Re-run rather than run once:
    # a view skipped for want of an input gains it when that input is registered later.
    # What the packet declares is passed separately from what is registered, so a view whose
    # refinements table exists but is not yet registered is skipped rather than built without
    # its guard -- which would answer, wrongly, instead of not answering.
    register_views(connection, [sql_name(r.resource_id) for r in declared])


def named_in(query: str, declared: Sequence[Resource]) -> set[str]:
    """Which declared tables a query mentions, including the ones its views are built on.

    Registering a table a query does not use costs one footer read; leaving out one it does
    use fails the query, so this errs towards registering. Matching is on whole words, so a
    name inside a string literal or a column name still counts -- which is the safe way to
    be wrong.
    """
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", query))
    needed = set(words)
    for view, spec in VIEWS.items():
        if view in words:
            needed |= set(spec["declared"][0]) | set(spec["inherited"][0]) | {spec["refinements"]}
    return {r.resource_id for r in declared if sql_name(r.resource_id) in needed}


#: How the SQL path resolves what inherits its clock's observation window (Part 01 §2.3), as
#: ``{view: spec}``.
#:
#: A packet that needs no refinement does not carry the table to refine with -- units inherit
#: their clock's window in the common case, so `core.unit_observation_intervals` is absent --
#: and DuckDB binds a view at creation rather than deferring. So the view is assembled from the
#: parts that can bind: the declaring branch is dropped when its table is absent, and the
#: inheriting branch's `NOT EXISTS` guard is dropped with it, being vacuously true.
#:
#: This restates the CTEs inside the registry's two `within_observation` rules rather than
#: sharing code with them, and the duplication is deliberate: a rule may name only registry
#: resources (Part 11 §3), so it cannot depend on a view this reader happens to register.
#: `tests/test_observation.py` asserts the two agree on the same packet, which is drift
#: protection without the coupling.
VIEWS: dict[str, dict[str, Any]] = {
    "unit_observation": {
        "refinements": "core_unit_observation_intervals",
        # A unit declares its own clock (Part 02 §12.1), so neither arm reaches through
        # `core.sorting_runs`.
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


__all__: list[str] = []
