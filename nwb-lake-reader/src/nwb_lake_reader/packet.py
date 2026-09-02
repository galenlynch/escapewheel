"""The packet: a dataset bundle under a declared physical profile."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as pads

from .clocks import NotAligned, anchors, declared_bound, mapped, stored_span
from .dictionaries import as_dictionary, constant
from .errors import NoTimeOrigin, ResourceNotFoundError, ResourceUnreadableError, UnsupportedCodecError
from .manifest import Manifest, Resource
from .resources import ArrayResource, TableResource
from .runs import Ambiguity
from .runs import check as _check_runs

if TYPE_CHECKING:  # pragma: no cover
    import duckdb

#: What a column constraint may be: a scalar for equality, a two-item tuple for a closed
#: range, or None to leave the column unconstrained.
Predicate = str | int | float | bool | tuple[Any, Any] | None

REGISTRY_PATH = "schemas/logical_schemas.json"

#: Zarr codecs every conforming reader must support (R3 §7.2). Declared here so a packet
#: requiring more can be rejected before it is opened. A resource declaring a codec outside
#: this set is refused only when it is the one being opened (R15 §2).
BASELINE_CODECS = frozenset({"none", "gzip", "zstd"})

#: Ask for ticks exactly as the file stores them. Spikes are counted on the probe that
#: recorded them, so stored ticks from two probes are not comparable and neither is a stored
#: tick against a behavioural event -- which is why reaching them takes saying so.
STORED = "stored"


#: The activities whose runs produce units and spikes, so the accessors returning those know
#: what to check for currency (R41 §2.4). An accessor already names one resource; naming what
#: produces it is not the general activity-to-table map R44 §2.4 rejects, which an extension's
#: tables could never be added to.
SORTING_ACTIVITIES = ("spike_sorting", "curation")


class Packet:
    """A packet opened for reading.

    Resolves resources through the manifest rather than by filename convention, so a
    packet that partitions a table or relocates a file stays readable without changes here.
    """

    def __init__(self, root: Path, manifest: Manifest) -> None:
        """Wrap an already-parsed manifest at a packet root.

        Parameters
        ----------
        root : Path
            Packet root directory.
        manifest : Manifest
            The parsed manifest.
        """
        self._root = root
        self._manifest = manifest
        self._by_id = {r.resource_id: r for r in manifest.resources}
        self._anchor_cache: dict[str, Any] | None = None
        self._reference_cache: str | None = None
        self._origin_cache: dict[str | None, tuple[int, int, int]] = {}
        self._bound_cache: float | None = None
        self._ambiguity_cache: tuple[Ambiguity, ...] | None = None

    @property
    def root(self) -> Path:
        """The packet root directory."""
        return self._root

    @property
    def manifest(self) -> Manifest:
        """The parsed manifest."""
        return self._manifest

    @property
    def sessions(self) -> tuple[str, ...]:
        """Every session this packet contains."""
        return self._manifest.sessions

    def __repr__(self) -> str:
        """Return a short representation naming the packet and its resource count."""
        return f"<Packet {self._manifest.packet_id!r} at {self._root} with {len(self._by_id)} resources>"

    # -- resources ------------------------------------------------------------------

    def resources(self, *, layer: str | None = None, kind: str | None = None) -> tuple[Resource, ...]:
        """List declared resources, optionally filtered.

        Parameters
        ----------
        layer : str, optional
            Restrict to one layer, e.g. ``core``.
        kind : str, optional
            Restrict to one kind, e.g. ``table``.

        Returns
        -------
        tuple of Resource
            Matching resources, in manifest order.
        """
        return tuple(
            r
            for r in self._manifest.resources
            if (layer is None or r.layer == layer) and (kind is None or r.kind == kind)
        )

    def resource(self, resource_id: str) -> Resource:
        """Look up one resource by ID.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        Resource
            The declared resource.

        Raises
        ------
        ResourceNotFoundError
            If the manifest declares no such resource.
        """
        try:
            return self._by_id[resource_id]
        except KeyError:
            known = ", ".join(sorted(self._by_id)) or "none"
            raise ResourceNotFoundError(f"{resource_id!r} is not declared; the packet has: {known}") from None

    def path(self, resource_id: str) -> Path:
        """Resolve a resource's URI to a filesystem path.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        Path
            The resolved path.

        Raises
        ------
        ResourceUnreadableError
            If the resolved path does not exist.
        """
        return self.table_resource(resource_id).path

    def table_resource(self, resource_id: str) -> TableResource:
        """Get a readable handle for a resource.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        TableResource
            A handle that can read, open lazily, or register the resource.
        """
        return TableResource(self.resource(resource_id), self._root)

    def array_resource(self, resource_id: str) -> ArrayResource:
        """Get a readable handle for a dense array resource.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        ArrayResource
            A handle that can answer what the array is without Zarr, and read it with Zarr.
        """
        return ArrayResource(self.resource(resource_id), self._root)

    def array_resources(self) -> tuple[ArrayResource, ...]:
        """Every dense array the packet declares, in manifest order.

        Returns
        -------
        tuple of ArrayResource
            One handle per `dense_array_asset` resource.
        """
        return tuple(ArrayResource(resource, self._root) for resource in self.resources(kind="dense_array_asset"))

    # -- the registry the packet carries --------------------------------------------

    @property
    def registry(self) -> dict[str, Any] | None:
        """The schema registry embedded in the packet, if it carries one.

        A packet SHOULD embed its registry so that it stays self-describing as the
        reference registry moves on. Reading does not require it; validation does.

        Returns
        -------
        dict or None
            The parsed registry, or None if the packet does not embed one.
        """
        path = self._root / REGISTRY_PATH
        if not path.is_file():
            return None
        parsed: dict[str, Any] = json.loads(path.read_text())
        return parsed

    # -- codec capability -------------------------------------------------------------

    def check_codecs(self, resource_id: str, supported: Iterable[str] = BASELINE_CODECS) -> None:
        """Check that this reader can open one resource, before opening it.

        Codecs are a property of a resource, not of a packet (R15 §2). A packet may
        reference an array in a codec this reader lacks while its own arrays are readable,
        so a missing codec disqualifies that resource and nothing else.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        supported : iterable of str, optional
            Codecs this reader can decode. Defaults to the portable-profile baseline.

        Raises
        ------
        UnsupportedCodecError
            If the resource uses a codec that is not supported.
        """
        missing = sorted(set(self.resource(resource_id).codecs) - set(supported))
        if missing:
            raise UnsupportedCodecError(f"{resource_id} uses codecs this reader does not support: {', '.join(missing)}")

    def unopenable(self, supported: Iterable[str] = BASELINE_CODECS) -> dict[str, tuple[str, ...]]:
        """Report which resources this reader cannot open, and why.

        The packet-level counterpart to :meth:`check_codecs`. It reports rather than raises,
        because a codec used by one resource says nothing about the rest.

        Parameters
        ----------
        supported : iterable of str, optional
            Codecs this reader can decode. Defaults to the portable-profile baseline.

        Returns
        -------
        dict
            Resource ID to the codecs it needs that are unsupported. Empty when the whole
            packet is readable.
        """
        available = set(supported)
        return {
            r.resource_id: tuple(sorted(set(r.codecs) - available))
            for r in self._manifest.resources
            if set(r.codecs) - available
        }

    # -- tabular access ---------------------------------------------------------------

    def table(
        self,
        resource_id: str,
        *,
        columns: list[str] | None = None,
        decode: bool = True,
        **where: Predicate,
    ) -> pa.Table:
        """Read a table resource into memory, optionally narrowed.

        Constraints are pushed into the Parquet reader rather than applied afterwards, so
        row groups that cannot match are never decompressed. Selecting one unit from nine
        million spikes takes 4 ms this way against 25 ms for reading and then filtering.

        Reading goes through PyArrow, not a SQL engine, so a packet stays readable with the
        ``sql`` extra absent.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        columns : list of str, optional
            Read only these columns. Reading every column is the default.
        decode : bool, default True
            Return plain strings. Pass False to keep the columns the file dictionary-encoded
            as `dictionary<string, int32>`, which reading a whole identity column wants:
            `unit_id` over 287 M spikes is 0.23 s and 1.15 GB that way against 2.29 s and
            12.75 GB decoded, and the decoded read needs 13.6 GB to finish. Filtered reads
            never come close, so the default is the predictable type rather than the fast one.

            Whichever is chosen applies to both access paths, so the schema does not depend on
            whether a constraint was passed. Named like `columns`, this shadows a constraint
            on a column of the same name.
        **where : str, int, float, bool, tuple, or None
            Column constraints. A scalar means equality, a two-item tuple means a closed
            range, and ``None`` leaves the column unconstrained.

        Returns
        -------
        pyarrow.Table
            Matching rows, in stored order.

        Examples
        --------
        >>> packet.table("core.events", event_type="reward")           # doctest: +SKIP
        >>> packet.table("core.spike_events", t_tick=(30_000, 60_000))  # doctest: +SKIP
        """
        handle = self.table_resource(resource_id)
        if not where:
            # Projection is not a filter. Sending it through the dataset would decode every
            # row and re-encode it, which on a whole identity column is 4.6 s against 0.3 s.
            return handle.to_arrow(columns=columns, decode=decode)
        # Read decoded, which is much the faster way to run a filter, then put the type back.
        # The route differs between a whole read and a filtered one; the type returned does
        # not, because a caller should not have to know which branch it took.
        table = handle.dataset(decode=True).to_table(columns=columns, filter=self._predicate(where))
        return table if decode else as_dictionary(table, handle.dictionary_columns())

    def scan(self, resource_id: str, *, decode: bool = True) -> pads.Dataset:
        """Open a resource lazily, without reading it.

        Use this for what constraints cannot express: streaming a resource too large to
        materialize, handing a dataset to another library, or composing an expression that
        :meth:`table` does not cover.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        pyarrow.dataset.Dataset
            A lazy dataset over the resource.
        """
        return self.table_resource(resource_id).dataset(decode=decode)

    def duckdb(self, *, connection: duckdb.DuckDBPyConnection | None = None) -> duckdb.DuckDBPyConnection:
        """Register every table resource as a view and return the connection.

        Views are named by flattening the dotted resource ID, so ``core.trials`` is queried
        as ``core_trials``.

        Parameters
        ----------
        connection : duckdb.DuckDBPyConnection, optional
            An existing connection to register into. A new in-memory one is created if
            omitted.

        Returns
        -------
        duckdb.DuckDBPyConnection
            The connection, with every readable table resource registered.
        """
        if connection is not None:
            con = connection
        else:
            try:
                import duckdb as _duckdb
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise ImportError(
                    "SQL access requires duckdb; install the 'sql' extra. It is optional because a "
                    "complete read path exists without it: table(), the accessors, and "
                    "TableResource.dataset() all go through PyArrow."
                ) from exc
            con = _duckdb.connect()
        for resource in self.resources(kind="table") + self.resources(kind="materialized_table"):
            handle = TableResource(resource, self._root)
            try:
                handle.register(con)
            except ResourceUnreadableError:
                continue
        return con

    def sql(self, query: str) -> pa.Table:
        """Run a query against this packet's tables.

        Parameters
        ----------
        query : str
            SQL referring to resources by their flattened names.

        Returns
        -------
        pyarrow.Table
            The result.
        """
        return self.duckdb().sql(query).to_arrow_table()

    # -- convenience accessors --------------------------------------------------------

    @staticmethod
    def _predicate(where: Mapping[str, Predicate]) -> pads.Expression | None:
        """Build a dataset expression from column constraints.

        A scalar means equality; a two-item tuple means a closed range; ``None`` means the
        column is unconstrained. An unknown column raises when the expression is applied,
        rather than silently matching nothing.
        """
        expression: pads.Expression | None = None
        for column, value in where.items():
            if value is None:
                continue
            field = pads.field(column)
            if isinstance(value, tuple):
                low, high = value
                term = (field >= low) & (field <= high)
            else:
                term = field == value
            expression = term if expression is None else expression & term
        return expression

    def trials(self, *, session_id: str | None = None, condition_id: str | None = None) -> pa.Table:
        """Read ``core.trials``, optionally filtered.

        Parameters
        ----------
        session_id : str, optional
            Keep only this session.
        condition_id : str, optional
            Keep only this experimental condition.

        Returns
        -------
        pyarrow.Table
            Matching trials.
        """
        return self.table("core.trials", session_id=session_id, condition_id=condition_id)

    def units(self, *, session_id: str | None = None, quality_label: str | None = None) -> pa.Table:
        """Read ``core.units``, optionally filtered.

        Parameters
        ----------
        session_id : str, optional
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
            to read (R41 §2.4). Returning both concatenated is two complete sets of units with
            nothing marking the seam, so every count taken over the result is wrong. Read
            ``table("core.units")`` to get the rows anyway.
        """
        _check_runs(self, SORTING_ACTIVITIES)
        return self.table("core.units", session_id=session_id, quality_label=quality_label)

    def events(
        self,
        *,
        event_type: str | None = None,
        session_id: str | None = None,
        t_tick: tuple[int, int] | None = None,
        clock: str | None = None,
        seconds: bool = False,
    ) -> pa.Table:
        """Read ``core.events``, on the packet's reference clock unless told otherwise.

        Parameters
        ----------
        event_type : str, optional
            Keep only events of this type. The vocabulary is open, so an unrecognized
            value is not an error, only empty.
        session_id : str, optional
            Keep only this session.
        t_tick : tuple of int, optional
            Keep only events within this closed tick range, stated on the clock the result
            comes back on -- so a range and the ticks it selects are always in the same space.
            A loose translation of it is pushed into the Parquet reader for pruning and the
            exact one applied after mapping.
        clock : str, optional
            The clock to return ticks on. Defaults to :meth:`reference_clock`; pass
            :data:`STORED` for the ticks the file holds.
        seconds : bool, default False
            Add a `t_second` column from the packet's declared origin (R39 §2.3). Refuses on
            a packet that declares none, and on ticks that are not on the reference clock.

        Returns
        -------
        pyarrow.Table
            Matching events, with `t_tick` on `clock` and `clock_id` naming it.
        """
        found = self.table(
            "core.events", event_type=event_type, session_id=session_id, t_tick=self._span(t_tick, clock)
        )
        if clock != STORED:
            found = self._narrowed(self.on_clock(found, clock), t_tick)
        return self.seconds(found, session_id=session_id) if seconds else found

    def spike_times(
        self,
        unit_id: str | None = None,
        *,
        units: pa.Table | None = None,
        session_id: str | None = None,
        sorting_run_id: str | None = None,
        curation_id: str | None = None,
        t_tick: tuple[int, int] | None = None,
        clock: str | None = None,
        seconds: bool = False,
    ) -> pa.Table:
        """Read spike times for one unit, or for a table of them.

        **On the reference clock by default.** A spike is counted on the probe that recorded
        it, so stored ticks from two probes are not comparable and neither is a stored tick
        against a behavioural event; returning them by default makes the wrong answer the
        easy one. `clock_id` comes back alongside `t_tick` either way, because a tick has no
        meaning without the clock it was counted on.

        A unit is identified by ``(session_id, unit_id, sorting_run_id, curation_id)``, never
        by ``unit_id`` alone. Passing `units` carries that whole identity, so a packet holding
        two sortings of the same unit cannot be read ambiguously; naming `unit_id` on its own
        leaves the caller to supply the rest and to notice when they have not.

        It is also the fast path. `core.units` is thousands of rows and `core.spike_events` is
        hundreds of millions, so resolving which units are wanted in the small table and
        pushing their keys into the large one is the shape this format is built for: the keys
        are compared against row-group statistics, and groups that cannot match are never
        read. The alternative -- reading identity columns back out of the spike table to work
        out which rows are wanted -- decodes one string per spike and costs orders of
        magnitude more.

        Parameters
        ----------
        unit_id : str, optional
            One unit. Mutually exclusive with `units`.
        units : pyarrow.Table, optional
            Units to read, as returned by :meth:`units` and filtered however the caller
            likes. Only its key columns are used; any others are ignored.
        session_id, sorting_run_id, curation_id : str, optional
            Narrow the identifying context when naming a single `unit_id`.
        t_tick : tuple of int, optional
            Keep only spikes within this closed tick range, stated on the clock the result
            comes back on, not on the unit's stored clock -- a range and the ticks it selects
            are always in the same space. Pass `clock=STORED` for both in stored ticks.
        clock : str, optional
            The clock to return ticks on. Defaults to :meth:`reference_clock`; pass
            :data:`STORED` for the ticks the file holds. Mapping drops a spike the anchors
            cannot place, exactly as `analysis.spike_events` does.
        seconds : bool, default False
            Add a `t_second` column from the packet's declared origin (R39 §2.3). Refuses on
            a packet that declares none, and on ticks that are not on the reference clock.

        Returns
        -------
        pyarrow.Table
            Columns ``t_tick`` and ``clock_id``, in stored order.

        Raises
        ------
        ValueError
            If both or neither of `unit_id` and `units` are given.
        AmbiguousRun
            If the packet does not say which sorting to read (R41 §2.4).

        Examples
        --------
        >>> packet.spike_times(units=packet.units(quality_label="sua"))  # doctest: +SKIP
        """
        if (unit_id is None) == (units is None):
            raise ValueError("name exactly one of unit_id or units")
        _check_runs(self, SORTING_ACTIVITIES)
        if unit_id is not None:
            found = self.table(
                "core.spike_events",
                columns=["t_tick", "clock_id"],
                unit_id=unit_id,
                session_id=session_id,
                sorting_run_id=sorting_run_id,
                curation_id=curation_id,
                t_tick=self._span(t_tick, clock),
            )
            if clock != STORED:
                found = self._narrowed(self.on_clock(found, clock), t_tick)
            return self.seconds(found, session_id=session_id) if seconds else found

        assert units is not None  # the exclusivity check above settles this
        keys = self._reference_columns("core.spike_events", "core.units")
        missing = [k for k in keys if k not in units.schema.names]
        if missing:
            raise ValueError(f"units is missing {missing}, which identify a unit in this packet")
        # The values must match the type the scan produces. `units` comes back with its
        # identity columns dictionary-encoded -- that is what makes reading them cheap -- and
        # a dictionary array will not compare against a string column.
        tests = []
        for key in keys:
            values = units.column(key).unique()
            if pa.types.is_dictionary(values.type):
                values = values.cast(pa.string())
            tests.append(pc.field(key).isin(values))
        wanted = tests[0]
        for test in tests[1:]:
            wanted = wanted & test
        if (pushed := self._span(t_tick, clock)) is not None:
            wanted = wanted & (pc.field("t_tick") >= pushed[0]) & (pc.field("t_tick") <= pushed[1])
        found = self.scan("core.spike_events").to_table(columns=["t_tick", "clock_id"], filter=wanted)
        if clock != STORED:
            found = self._narrowed(self.on_clock(found, clock), t_tick)
        return self.seconds(found, session_id=session_id) if seconds else found

    def reference_clock(self, *, session_id: str | None = None) -> str:
        """Return the clock this packet reports times on (R27 §2).

        Parameters
        ----------
        session_id : str, optional
            Which session's reference to return. Only needed where a multi-session packet's
            sessions disagree, which is refused rather than resolved by picking one.

        Returns
        -------
        str
            The declared `clock_id`.

        Raises
        ------
        NotAligned
            If no session declares one, if the named session does not, or if sessions declare
            different clocks and none was named.
        """
        if session_id is None and self._reference_cache is not None:
            return self._reference_cache
        table = self.table("core.sessions")
        if "reference_clock_id" not in table.column_names:
            raise NotAligned("core.sessions carries no reference_clock_id (R27 §2)")
        declared = {
            session: clock
            for session, clock in zip(
                table.column("session_id").to_pylist(), table.column("reference_clock_id").to_pylist(), strict=True
            )
            if clock
        }
        if session_id is not None:
            if session_id not in declared:
                raise NotAligned(f"session {session_id!r} declares no reference_clock_id (R27 §2)")
            return str(declared[session_id])
        named = sorted(set(declared.values()))
        if not named:
            raise NotAligned("no session declares a reference_clock_id (R27 §2)")
        if len(named) > 1:
            raise NotAligned(f"sessions declare different reference clocks {named}; name a session_id")
        self._reference_cache = str(named[0])
        return self._reference_cache

    def t_zero(self, *, session_id: str | None = None) -> int:
        """Return the session's time origin, on the reference clock (R39 §2.2).

        The earliest tick at which any of the session's clocks was observing. It is read from
        `core.sessions.t_zero_tick` rather than recomputed: the writer took the minimum across
        clocks through R13's mapping, which is arithmetic a reader should not have to repeat
        and would not repeat identically.

        Raises
        ------
        NoTimeOrigin
            If the packet declares none.
        """
        return self._origin(session_id)[0]

    def seconds(self, table: pa.Table, *, session_id: str | None = None) -> pa.Table:
        """Add a `t_second` column to a table whose ticks are on the reference clock.

        R39 §2.3: `(t_tick - t_zero_tick) / reference_tick_rate`, taking the rate as the
        declared rational so nothing is lost to the rounded `tick_rate_hz`.

        The tick stays. Seconds are derived and this does not pretend otherwise -- a caller
        that needs to compare, join or bucket still has the exact integer beside the float.

        Seconds may be negative. Data outside its own observation window is a real and
        reported condition (R38 §2.5), and the origin is not clamped to hide it.

        Raises
        ------
        NoTimeOrigin
            If the packet declares no origin.
        NotAligned
            If the table's ticks are not on the reference clock, since seconds from any other
            clock's ticks would be a different quantity wearing the same name.
        """
        origin, num, den = self._origin(session_id)
        reference = self.reference_clock(session_id=session_id)
        present = _clocks_in(_flat(table.column("clock_id"))) if table.num_rows else [reference]
        if present != [reference]:
            raise NotAligned(
                f"seconds are defined on {reference!r} (R39 §2.3), but these ticks are on "
                f"{present}; map them with on_clock first"
            )
        offset = pc.subtract(table.column("t_tick"), pa.scalar(origin, pa.int64()))
        return table.append_column("t_second", pc.divide(pc.cast(offset, pa.float64()), float(num) / float(den)))

    def _origin(self, session_id: str | None) -> tuple[int, int, int]:
        """Return the origin and the reference clock's rational rate, read once per session."""
        if session_id in self._origin_cache:
            return self._origin_cache[session_id]
        sessions = self.table("core.sessions")
        if "t_zero_tick" not in sessions.column_names:
            raise NoTimeOrigin("core.sessions carries no t_zero_tick, so seconds are undefined (R39 §2.3)")
        declared = {
            session: tick
            for session, tick in zip(
                sessions.column("session_id").to_pylist(), sessions.column("t_zero_tick").to_pylist(), strict=True
            )
            if tick is not None
        }
        if session_id is not None:
            if session_id not in declared:
                raise NoTimeOrigin(f"session {session_id!r} declares no t_zero_tick (R39 §2.3)")
            origin = int(declared[session_id])
        else:
            found = sorted(set(declared.values()))
            if not found:
                raise NoTimeOrigin("no session declares a t_zero_tick, so seconds are undefined (R39 §2.3)")
            if len(found) > 1:
                raise NoTimeOrigin(f"sessions declare different origins {found}; name a session_id")
            origin = int(found[0])
        num, den = self._tick_rate(self.reference_clock(session_id=session_id))
        self._origin_cache[session_id] = (origin, num, den)
        return self._origin_cache[session_id]

    def _tick_rate(self, clock_id: str) -> tuple[int, int]:
        """Return a clock's rational tick rate, which R39 §2.3 prefers to `tick_rate_hz`."""
        clocks = self.table("core.clocks")
        names = clocks.column("clock_id").to_pylist()
        if clock_id not in names:
            raise NotAligned(f"core.clocks declares no {clock_id!r}, so its rate is unknown")
        row = names.index(clock_id)
        num = clocks.column("tick_rate_num")[row].as_py()
        den = clocks.column("tick_rate_den")[row].as_py() if "tick_rate_den" in clocks.column_names else 1
        if not num:
            raise NotAligned(f"{clock_id!r} declares no tick_rate_num, so seconds cannot be derived")
        return int(num), int(den or 1)

    def on_clock(self, table: pa.Table, clock: str | None = None, *, bound: float | None = None) -> pa.Table:
        """Return `table` with its ticks on one clock.

        A row whose tick the anchors cannot place is **dropped**, which is what R27 §5.3
        leaves undefined and what `analysis.spike_events` does with the same rows. Reading
        `core` through this and reading the materialized table therefore agree -- which is
        why the bound defaults to the one the packet's writer established and recorded
        (R37 §3.3), not to R27 §5.3's. A reader mapping at a narrower bound than the writer
        used drops rows the packet's own derived table kept, and the two disagree about
        which spikes exist.

        Parameters
        ----------
        table : pyarrow.Table
            Any table carrying `t_tick` and `clock_id`.
        clock : str, optional
            The clock to map onto. Defaults to :meth:`reference_clock`.
        bound : float, optional
            How far from an anchor the mapping stays defined, in median anchor intervals.
            Defaults to :func:`~nwb_lake_reader.clocks.declared_bound`.

        Returns
        -------
        pyarrow.Table
            The same columns, `t_tick` on `clock` and `clock_id` naming it, minus the rows
            where the mapping is undefined.
        """
        if table.num_rows == 0:
            return table
        columns = {name: _flat(table.column(name)) for name in ("t_tick", "clock_id")}
        present = _clocks_in(columns["clock_id"])
        target = clock or self._default_clock(present)
        if present == [target]:
            # Already there. Worth the check: it is the whole single-clock case, and it keeps
            # a packet with no anchors readable.
            return table
        ticks, keep = mapped(
            pa.record_batch(columns), target, self._anchors(), self._bound() if bound is None else bound
        )
        names = table.column_names
        out = table.set_column(names.index("t_tick"), "t_tick", pa.array(ticks))
        out = out.set_column(names.index("clock_id"), "clock_id", constant(target, table.num_rows))
        return out.filter(pa.array(keep))

    def _span(self, span: tuple[int, int] | None, clock: str | None) -> tuple[int, int] | None:
        """Widen a range stated on the result's clock into one the file can be pruned by."""
        if span is None or clock == STORED:
            return span
        try:
            target = clock or self.reference_clock()
        except NotAligned:
            return span
        return stored_span(self._anchors(), target, span)

    def _narrowed(self, table: pa.Table, span: tuple[int, int] | None) -> pa.Table:
        """Apply the caller's range exactly, now that every row is on one clock."""
        if span is None:
            return table
        ticks = table.column("t_tick")
        return table.filter(pc.and_(pc.greater_equal(ticks, span[0]), pc.less_equal(ticks, span[1])))

    def _default_clock(self, present: list[str]) -> str:
        """Which clock to map onto when the caller named none.

        The declared reference, or -- where a packet declares none -- the one clock the rows
        are already on, since there is then nothing to reconcile and nothing to get wrong.
        Rows spanning clocks with no reference declared are refused: that is exactly the case
        where returning them as stored invites a comparison that means nothing.
        """
        try:
            return self.reference_clock()
        except NotAligned:
            if len(present) == 1:
                return present[0]
            raise

    def _bound(self) -> float:
        """Return the bound the writer established, read once per packet."""
        if self._bound_cache is None:
            self._bound_cache = declared_bound(self)
        return self._bound_cache

    def _anchors(self) -> dict[str, Any]:
        """`core.clock_anchors` per clock, read once per packet.

        Cached because an accessor is called per unit: reading the anchor table for each of
        6,781 units would cost more than the spikes do.
        """
        if self._anchor_cache is None:
            self._anchor_cache = anchors(self)
        return self._anchor_cache

    def _reference_columns(self, resource_id: str, parent: str) -> list[str]:
        """Return the columns by which one resource references another, per the registry.

        The registry declares 46 of these and nothing read them. For spikes and units it is
        the four-column contextual identity, which is the whole reason to take it from the
        registry rather than write it out here and let the two drift.
        """
        registry = self.registry
        table = (registry or {}).get("tables", {}).get(resource_id, {})
        for reference in table.get("references", []):
            if reference["resource"] == parent:
                return list(reference["columns"])
        raise ResourceNotFoundError(f"the registry declares no reference from {resource_id} to {parent}")

    def distinct(self, resource_id: str, column: str) -> pa.ChunkedArray[Any]:
        """Return the distinct values of a column, from whichever table owns them.

        A foreign key means the parent table holds every value the child may carry, and it is
        the smaller table by construction -- `core.units` is thousands of rows where
        `core.spike_events` is hundreds of millions. So the answer comes from the parent, and
        the fact table is never scanned. Falls back to reading the column when no reference
        covers it, which is the honest thing rather than a wrong answer.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        column : str
            The column whose values are wanted.

        Returns
        -------
        pyarrow.Array
            The distinct values, unordered.
        """
        registry = self.registry
        table = (registry or {}).get("tables", {}).get(resource_id, {})
        for reference in table.get("references", []):
            if column not in reference["columns"]:
                continue
            at = reference["columns"].index(column)
            parent = reference["resource"]
            if parent not in {r.resource_id for r in self.resources()}:
                continue
            return self.table(parent, columns=[reference["resource_columns"][at]]).column(0).unique()
        return self.table(resource_id, columns=[column]).column(0).unique()


def _clocks_in(column: pa.Array) -> list[str]:
    """Distinct clock IDs in a column, read from its dictionary where it has one."""
    listed = column.dictionary if pa.types.is_dictionary(column.type) else pc.unique(column)
    return sorted({v for v in listed.to_pylist() if v is not None})


def _flat(column: Any) -> pa.Array:
    """Return one Array from a column that may arrive in chunks."""
    combined = column.combine_chunks() if isinstance(column, pa.ChunkedArray) else column
    if isinstance(combined, pa.ChunkedArray):
        return combined.chunk(0) if combined.num_chunks else combined.cast(combined.type).combine_chunks()
    return combined


def open_packet(path: str | Path, *, validate_manifest: bool = True) -> Packet:
    """Open a packet for reading.

    Parameters
    ----------
    path : str or Path
        Packet root directory.
    validate_manifest : bool, default True
        Whether to check the manifest against its JSON Schema before parsing.

    Returns
    -------
    Packet
        The opened packet.
    """
    root = Path(path)
    return Packet(root, Manifest.load(root, validate=validate_manifest))
