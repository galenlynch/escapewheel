"""Open one packet, and read its resources by ID.

- :func:`open_packet` -- open a packet at a local directory or a store prefix.
- :class:`Packet` -- list, resolve and read resources, acquire the registries the packet binds,
  and register tables with DuckDB.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
import pyarrow.dataset as pads

from . import clocks, duck
from .errors import RegistryFault, RegistryUnavailable, ResourceNotFoundError
from .location import Location, Rewrite, Sources, resolve_sources
from .manifest import Manifest, Resource
from .predicates import Predicate, both, expression, on_clock_constraints
from .protocols import Memo
from .registries import acquire, parse
from .resources import ArrayResource, TableResource, read_pool

if TYPE_CHECKING:  # pragma: no cover
    import duckdb

    from .protocols import PacketLike


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
        self._memo = Memo()

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

    @property
    def memo(self) -> Memo:
        """What the free functions have read from this packet and keep for its lifetime."""
        return self._memo

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
        # A shallow copy: each keeps its own answers from here on, and the two share `origins`.
        rebound._memo = copy(self._memo)
        rebound._manifest = replace(self._manifest, resources=resolved)
        rebound._by_id = {resource.resource_id: resource for resource in resolved}
        return rebound

    # -- tabular access ---------------------------------------------------------------

    def table(
        self,
        resource_id: str,
        *,
        columns: list[str] | None = None,
        on_clock: bool | int = False,
        seconds: bool = False,
        **where: Predicate,
    ) -> pa.Table:
        """Read a table resource into memory, optionally narrowed and put on one clock.

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
            Read only these columns. Reading every column is the default. With `on_clock` or
            `seconds`, include the columns each coordinate's clock is reached through.
        on_clock : bool or int, default False
            Map every coordinate onto the reference clock, or onto the clock given, by
            :func:`~escapewheel_reader.clocks.on_clock` with this `resource_id`.
        seconds : bool, default False
            Add a seconds column per coordinate, by :func:`~escapewheel_reader.clocks.seconds`.
            The coordinates must be on the reference clock, as `on_clock=True` leaves them.
        **where : str, int, float, bool, tuple, list, set, or None
            Column constraints. A scalar means equality, a two-item tuple a closed range, a list
            or set membership, and ``None`` leaves the column unconstrained. A constraint tests
            the column as returned: a coordinate's stored tick without `on_clock`, and its tick
            on the output clock with it, through :func:`~escapewheel_reader.predicates.tick_range`.
            Every row returned therefore satisfies every constraint as read. Without `on_clock`,
            a range on a coordinate whose rows are on several clocks compares ticks of different
            clocks.

        Returns
        -------
        pyarrow.Table
            Matching rows, in stored order.

        Examples
        --------
        >>> packet.table("core.events", event_type="reward")           # doctest: +SKIP
        >>> packet.table("core.spike_events", t_tick=(30_000, 60_000))  # doctest: +SKIP
        >>> packet.table("dynamic_foraging.trials", on_clock=True, seconds=True)  # doctest: +SKIP
        """
        if on_clock is False:
            wanted = expression(where)
        else:
            target = None if on_clock is True else int(on_clock)
            wanted = on_clock_constraints(self, resource_id, where, target)
        table = self._scanner(resource_id, columns, wanted).to_table()
        if on_clock is not False:
            table = clocks.on_clock(self, table, None if on_clock is True else int(on_clock), resource_id=resource_id)
        if seconds:
            table = clocks.seconds(self, table, resource_id=resource_id)
        return table

    def scanner(
        self,
        resource_id: str,
        *,
        columns: list[str] | None = None,
        filter: pads.Expression | None = None,
        **where: Predicate,
    ) -> pads.Scanner:
        """Narrow a table resource as :meth:`table` does, without reading it.

        The scanner carries the projection, the pushed-down constraints and the reader's memory
        pool, so reading it later costs what :meth:`table` costs. Polars, DuckDB and Arrow each
        consume one, directly or through ``to_reader()``; ``to_batches()`` streams a resource too
        large to hold.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        columns : list of str, optional
            Read only these columns. Reading every column is the default.
        filter : pyarrow.dataset.Expression, optional
            Any further expression, such as :func:`~escapewheel_reader.predicates.where` builds,
            ANDed with `where`.
        **where : str, int, float, bool, tuple, list, set, or None
            Column constraints, as for :meth:`table`.

        Returns
        -------
        pyarrow.dataset.Scanner
            A lazy, single-use scan of the matching rows, in stored order.

        Examples
        --------
        >>> reader = packet.scanner("core.spike_events", columns=["t_tick"], unit_id=7).to_reader()  # doctest: +SKIP
        """
        return self._scanner(resource_id, columns, both(expression(where), filter))

    def _scanner(
        self,
        resource_id: str,
        columns: list[str] | None,
        filter: pads.Expression | None,
    ) -> pads.Scanner:
        dataset = self.table_resource(resource_id).dataset()
        return dataset.scanner(columns=columns, filter=filter, memory_pool=read_pool())

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
        alongside where their inputs are present, so a rate has a denominator without the caller
        writing the join.

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
        return duck.registered(
            self._root, self.resources(kind="table"), connection=connection, tables=tables, for_query=for_query
        )

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
        A committed packet records where its writer reached each resource, so this is how the
        same bytes are reached from somewhere else without editing the packet. Longest prefix
        wins.
    sources : iterable, optional
        Source resolution documents, as mappings or as paths to read. Consulted
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
