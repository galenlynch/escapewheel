"""Open one packet, and read its resources by ID.

- :func:`open_packet` -- open a packet at a local directory or a store prefix.
- :class:`Packet` -- list, resolve and read resources, acquire the registries the packet binds,
  and register tables with DuckDB.
"""

from __future__ import annotations

import contextlib
import re
import warnings
from collections.abc import Collection, Iterable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
import pyarrow.dataset as pads

from .errors import RegistryFault, RegistryUnavailable, ResourceNotFoundError, ResourceUnreadableError
from .location import Location, Rewrite, Sources, resolve_sources
from .manifest import Manifest, Resource
from .observation import VIEWS, register_views
from .registries import acquire, parse
from .resources import ArrayResource, TableResource
from .runs import Ambiguity
from .sql import sql_name

if TYPE_CHECKING:  # pragma: no cover
    import duckdb

    # By name as well as by module: inside the class body `duckdb` is the method, so a
    # `duckdb.DuckDBPyConnection` annotation after it resolves to the wrong thing.
    from duckdb import DuckDBPyConnection

    from .protocols import PacketLike

#: What a column constraint may be: a scalar for equality, a two-item tuple for a closed
#: range, or None to leave the column unconstrained.
Predicate = str | int | float | bool | tuple[Any, Any] | list[Any] | None


class Packet:
    """A packet opened for reading.

    Resolves resources through the manifest rather than by filename convention, so a
    packet that partitions a table or relocates a file stays readable without changes here.
    """

    def __init__(self, root: Location | Path | str, manifest: Manifest) -> None:
        """Wrap an already-parsed manifest at a packet root.

        Parameters
        ----------
        root : Location, Path, or str
            Packet root: a local directory or a store prefix such as ``s3://bucket/prefix``.
        manifest : Manifest
            The parsed manifest.
        """
        self._root = Location.of(root)
        # Acquired on first need, so opening a packet or listing its resources reads no registry.
        self._acquired: dict[str, bytes] = {}
        self._documents: dict[str, dict[str, Any]] = {}
        resolved = tuple(replace(resource, resolve=self._declaration) for resource in manifest.resources)
        self._manifest = replace(manifest, resources=resolved)
        self._by_id = {r.resource_id: r for r in resolved}
        self._anchor_cache: dict[str, Any] | None = None
        self._reference_cache: int | None = None
        self._origin_cache: dict[int | None, tuple[int, int, int]] = {}
        self._bound_cache: float | None = None
        self._ambiguity_cache: tuple[Ambiguity, ...] | None = None
        self._support_cache: pa.Table | None = None

    @property
    def root(self) -> Path:
        """The packet root directory.

        Raises
        ------
        ResourceUnreadableError
            If the packet is in a store, which has no directory. Use :attr:`location`.
        """
        return self._root.path

    @property
    def location(self) -> Location:
        """Where the packet is, local or in a store."""
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

    def resources(
        self,
        *,
        content_class: str | None = None,
        layer: str | None = None,
        kind: str | None = None,
    ) -> tuple[Resource, ...]:
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
        selected_class = content_class if content_class is not None else layer
        return tuple(
            r
            for r in self._manifest.resources
            if (selected_class is None or r.content_class == selected_class) and (kind is None or r.kind == kind)
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
            raise ResourceNotFoundError(
                f"{resource_id!r} is not declared; the packet has: {known}", resource_id=resource_id
            ) from None

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

    def array(self, resource_id: str) -> Any:
        """Open a declared array for reading values.

        The counterpart of :meth:`table`, and Packet's for the same reason: both are resolution
        and IO, which is what this class is for, rather than a transformation over what they
        return. Equivalent to ``array_resource(resource_id).open()``; use the handle directly
        for `shape`, `dtype`, `codecs` or a chunk-aligned :meth:`~ArrayResource.read`, none of
        which need the array opened.

        Zarr is an optional dependency; install it with the ``arrays`` extra.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        zarr.Array
            The array, opened read-only.

        Raises
        ------
        ResourceNotFoundError
            If the manifest declares no such resource.
        ResourceUnreadableError
            If the resource does not resolve to a readable store.
        UnsupportedCodecError
            If Zarr cannot decode a codec the array uses; other resources stay readable.

        Examples
        --------
        >>> packet.array("core.waveform_mean")[0]  # doctest: +SKIP
        """
        return self.array_resource(resource_id).open()

    # -- the registry the packet carries --------------------------------------------

    def registry_bytes(self, registry_id: str) -> bytes:
        """One bound registry's exact document bytes, verified against its descriptor.

        Parameters
        ----------
        registry_id : str
            A member name of the manifest's `registries` map.

        Returns
        -------
        bytes
            The decompressed document, whose SHA-256 equals the descriptor's.

        Raises
        ------
        RegistryUnavailable
            If the manifest binds no such registry, or it is missing, unreadable, or fails its
            digest. Nothing is substituted for it (Part 04 §10).
        """
        if registry_id not in self._acquired:
            binding = self._manifest.registries.get(registry_id)
            if binding is None:
                raise RegistryUnavailable(registry_id, RegistryFault.MISSING, "the manifest binds no such registry")
            self._acquired[registry_id] = acquire(self._root, binding)
        return self._acquired[registry_id]

    def registry_document(self, registry_id: str) -> dict[str, Any]:
        """One bound registry, decoded for declaration lookup and not otherwise checked.

        Parameters
        ----------
        registry_id : str
            A member name of the manifest's `registries` map.

        Returns
        -------
        dict
            The registry document.

        Raises
        ------
        RegistryUnavailable
            If the registry cannot be acquired or is not a JSON object.
        """
        if registry_id not in self._documents:
            document = self.registry_bytes(registry_id)
            self._documents[registry_id] = parse(self._manifest.registries[registry_id], document)
        return self._documents[registry_id]

    @property
    def registry(self) -> dict[str, Any]:
        """The core registry the packet binds, acquired on first use.

        Raises
        ------
        RegistryUnavailable
            If the manifest binds no core registry, or it cannot be acquired.
        """
        core = self._manifest.core
        if core is None:
            raise RegistryUnavailable("core", RegistryFault.MISSING, "the manifest binds no core registry")
        return self.registry_document(core.registry_id)

    def extensions(self) -> dict[str, dict[str, Any]]:
        """Every extension registry the packet binds, by registry ID (Part 04 §8).

        Reading core never needs one -- Part 09 §6.1 forbids core to reference an extension --
        so only a caller that asks acquires them.

        Returns
        -------
        dict
            Registry ID to registry document.

        Raises
        ------
        RegistryUnavailable
            If a bound extension registry cannot be acquired. It is not silently left out.
        """
        return {name: self.registry_document(name) for name in self._manifest.extensions}

    def _declaration(self, declaration_id: str) -> Mapping[str, Any] | None:
        """Resolve a declaration in the bound registry its namespace selects, acquiring it once."""
        binding = self._manifest.binding_for(declaration_id)
        if binding is None:
            return None
        declarations = self.registry_document(binding.registry_id).get("resources")
        found = declarations.get(declaration_id) if isinstance(declarations, Mapping) else None
        return found if isinstance(found, Mapping) else None

    def with_declarations(self, *documents: Mapping[str, Any]) -> Packet:
        """Return this packet with manifest resources resolved against the given registries only.

        The validator passes the bound registries whose checked contexts may direct packet checks
        (Part 05 §14.5), so a declaration in a registry that failed binding resolves to nothing.
        """
        from copy import copy

        declarations: dict[str, Mapping[str, Any]] = {}
        for document in documents:
            resources = document.get("resources")
            if isinstance(resources, Mapping):
                declarations.update(resources)
        resolved = tuple(replace(resource, resolve=declarations.get) for resource in self._manifest.resources)
        rebound = copy(self)
        rebound._manifest = replace(self._manifest, resources=resolved)
        rebound._by_id = {resource.resource_id: resource for resource in resolved}
        return rebound

    # -- tabular access ---------------------------------------------------------------

    def table(
        self,
        resource_id: str,
        *,
        columns: list[str] | None = None,
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
            # Projection is not a filter, so it goes straight to the Parquet reader rather
            # than through a dataset scan that would touch every row.
            return handle.to_arrow(columns=columns)
        return handle.dataset().to_table(columns=columns, filter=self._predicate(where))

    def scan(self, resource_id: str) -> pads.Dataset:
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
        return self.table_resource(resource_id).dataset()

    def duckdb(
        self,
        *,
        connection: duckdb.DuckDBPyConnection | None = None,
        tables: Collection[str] | Literal["all"] | None = None,
        for_query: str | None = None,
    ) -> duckdb.DuckDBPyConnection:
        """Register table resources as views and return the connection.

        **Nothing is registered unless asked for.** DuckDB binds a view when it is created, and
        binding a Parquet view reads that file's footer -- free on local disk and a round trip
        per table in an object store, which for a 28-table packet was 3.5 s before the first
        query ran. Name what a query needs, or pass the query as `for_query` and let this work
        it out.

        Views are named by flattening the dotted resource ID, so ``core.intervals`` is queried
        as ``core_intervals``. `unit_observation` and `stream_observation` are registered
        alongside where their inputs are present, resolving R38's inheritance so a rate has a
        denominator without the caller writing the join.

        Parameters
        ----------
        connection : duckdb.DuckDBPyConnection, optional
            An existing connection to register into. A new in-memory one is created if
            omitted.
        tables : collection of str or "all", optional
            Which table resources to register, by dotted resource ID. ``"all"`` registers
            every one, which is what a validator wants and what a query rarely does. The
            default registers none.
        for_query : str, optional
            SQL to read table names out of, registering those and the inputs of any view it
            names. Combines with `tables`.

        Returns
        -------
        duckdb.DuckDBPyConnection
            The connection, with the requested table resources registered.
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
        declared = self._table_resources()
        if any(not TableResource(r, self._root).is_local for r in declared):
            _prepare_remote(con)
        wanted = {r.resource_id for r in declared} if tables == "all" else set(tables or ())
        if for_query is not None:
            wanted |= self._named_in(for_query)
        self._register(con, wanted)
        return con

    def _table_resources(self) -> tuple[Resource, ...]:
        """Every resource a SQL engine can be given, tabular or materialized."""
        return self.resources(kind="table")

    def _register(self, connection: DuckDBPyConnection, wanted: Collection[str]) -> None:
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
        for resource in self._table_resources():
            if resource.resource_id not in wanted or sql_name(resource.resource_id) in held:
                continue
            try:
                TableResource(resource, self._root).register(connection)
            except ResourceUnreadableError as exc:
                # Not silently: an unregistered view fails later as "table does not exist",
                # which points at the query rather than at the resource that could not be read.
                skipped.append(f"{resource.resource_id} ({exc})")
        if skipped:
            listed = "\n  ".join(skipped)
            warnings.warn(
                f"{len(skipped)} table(s) could not be registered and are absent from this connection:\n  {listed}",
                stacklevel=2,
            )
        # After the tables, because DuckDB binds a view at creation and one over a table this
        # packet does not declare is refused rather than deferred. Re-run rather than run once:
        # a view skipped for want of an input gains it when that input is registered later.
        # What the packet declares is passed separately from what is registered, so a view whose
        # refinements table exists but is not yet registered is skipped rather than built without
        # its guard (Part 01 §2.2) -- which would answer, wrongly, instead of not answering.
        register_views(connection, [sql_name(r.resource_id) for r in self._table_resources()])

    def _named_in(self, query: str) -> set[str]:
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
        return {r.resource_id for r in self._table_resources() if sql_name(r.resource_id) in needed}

    def sql(self, query: str) -> pa.Table:
        """Run a query against this packet's tables.

        The tables the query names are registered first, and only those: over an object store
        each registration is a round trip, so registering a packet's other 27 tables to answer
        a question about one is most of what the question costs.

        Parameters
        ----------
        query : str
            SQL referring to resources by their flattened names.

        Returns
        -------
        pyarrow.Table
            The result.
        """
        return self.duckdb(for_query=query).sql(query).to_arrow_table()

    @staticmethod
    def _predicate(where: Mapping[str, Predicate]) -> pads.Expression | None:
        """Build a dataset expression from column constraints.

        A scalar means equality; a two-item tuple means a closed range; a list or set means
        membership; ``None`` means the column is unconstrained. An unknown column raises when
        the expression is applied, rather than silently matching nothing.

        Membership exists because R91 §3.1 made one kind of event several streams: resolving a
        type gives a set of keys, and pushing them down is what lets row-group statistics prune
        rather than reading and filtering.
        """
        expression: pads.Expression | None = None
        for column, value in where.items():
            if value is None:
                continue
            field = pads.field(column)
            if isinstance(value, tuple):
                low, high = value
                term = (field >= low) & (field <= high)
            elif isinstance(value, (list, set, frozenset)):
                term = field.isin(list(value))
            else:
                term = field == value
            expression = term if expression is None else expression & term
        return expression


def _prepare_remote(connection: duckdb.DuckDBPyConnection) -> None:
    """Set up a connection that will read from an object store.

    Two settings, and getting either wrong fails quietly. `httpfs` is what lets DuckDB open an
    `s3://` URI at all. `enable_object_cache` keeps Parquet footers across queries and is worth
    16x on a repeated read -- 3.38 s against 0.21 s over one session's spikes -- with no error
    and no signal when it is off, which is the kind of wrong this package exists to prevent.

    Credentials are deliberately **not** set. Whether a store is reachable is a property of the
    caller's situation rather than of the packet (Part 04 §5.1), so a caller supplies its own secret;
    what this removes is the setup a caller cannot be expected to know.
    """
    with contextlib.suppress(Exception):  # an older duckdb, or an extension it cannot fetch
        connection.execute("INSTALL httpfs")
        connection.execute("LOAD httpfs")
    with contextlib.suppress(Exception):
        connection.execute("SET enable_object_cache=true")


def open_packet(
    path: str | Path | Location,
    *,
    rewrite: Rewrite | None = None,
    sources: Iterable[Sources | str | Path] | None = None,
) -> Packet:
    """Open a packet for reading.

    Parameters
    ----------
    path : str, Path, or Location
        Packet root: a local directory, or a store prefix such as ``s3://bucket/prefix``.
        Part 00 §3.3 admits both, and an object store is where a shared dataset lives.
    rewrite : Mapping, optional
        Declared-URI prefix to replacement, applied to every resource before it is resolved.
        Part 04 §5.1 makes reachability the reader's situation, and a committed packet records the
        writer's -- so this is how the same bytes are reached from somewhere else without
        editing bytes Part 04 §5.1 makes immutable. Longest prefix wins.
    sources : iterable, optional
        Source resolution documents (Part 04 §5.5), as mappings or as paths to read. Consulted
        before the packet root's own `sources.json`, in the order given; a path whose document
        fails the schema or declares an unknown version is refused.

    Returns
    -------
    Packet
        The opened packet.
    """
    root = Location.of(path, rewrite)
    return Packet(
        Location.of(root, rewrite, resolve_sources(root, sources)),
        Manifest.load(root),
    )


if TYPE_CHECKING:  # pragma: no cover
    # Checked statically: a `Packet` is what `PacketLike` describes.
    _PACKET_LIKE: type[PacketLike] = Packet

__all__ = ["Packet", "open_packet"]
