"""The packet: a dataset bundle under a declared physical profile."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as pads

from .errors import ResourceNotFoundError, ResourceUnreadableError, UnsupportedCodecError
from .manifest import Manifest, Resource
from .resources import ArrayResource, TableResource, as_dictionary

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
        """
        return self.table("core.units", session_id=session_id, quality_label=quality_label)

    def events(
        self,
        *,
        event_type: str | None = None,
        session_id: str | None = None,
        t_tick: tuple[int, int] | None = None,
    ) -> pa.Table:
        """Read ``core.events``, optionally filtered.

        Parameters
        ----------
        event_type : str, optional
            Keep only events of this type. The vocabulary is open, so an unrecognized
            value is not an error, only empty.
        session_id : str, optional
            Keep only this session.
        t_tick : tuple of int, optional
            Keep only events within this closed tick range. Ticks are only comparable
            within one clock, so pair this with a session or an event type that pins one.

        Returns
        -------
        pyarrow.Table
            Matching events.
        """
        return self.table("core.events", event_type=event_type, session_id=session_id, t_tick=t_tick)

    def spike_times(
        self,
        unit_id: str | None = None,
        *,
        units: pa.Table | None = None,
        session_id: str | None = None,
        sorting_run_id: str | None = None,
        curation_id: str | None = None,
        t_tick: tuple[int, int] | None = None,
    ) -> pa.Table:
        """Read spike times for one unit, or for a table of them.

        Returns ``clock_id`` alongside ``t_tick`` because a tick has no meaning without the
        clock it was counted on.

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
            Keep only spikes within this closed tick range, on the unit's own clock.

        Returns
        -------
        pyarrow.Table
            Columns ``t_tick`` and ``clock_id``, in stored order.

        Raises
        ------
        ValueError
            If both or neither of `unit_id` and `units` are given.

        Examples
        --------
        >>> packet.spike_times(units=packet.units(quality_label="sua"))  # doctest: +SKIP
        """
        if (unit_id is None) == (units is None):
            raise ValueError("name exactly one of unit_id or units")
        if unit_id is not None:
            return self.table(
                "core.spike_events",
                columns=["t_tick", "clock_id"],
                unit_id=unit_id,
                session_id=session_id,
                sorting_run_id=sorting_run_id,
                curation_id=curation_id,
                t_tick=t_tick,
            )

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
        if t_tick is not None:
            wanted = wanted & (pc.field("t_tick") >= t_tick[0]) & (pc.field("t_tick") <= t_tick[1])
        return self.scan("core.spike_events").to_table(columns=["t_tick", "clock_id"], filter=wanted)

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
