"""Open one packet, and read its resources by ID.

- :func:`open_packet` -- open a packet at a local directory or a store prefix.
- :class:`Packet` -- list, resolve and read resources, acquire the registries the packet binds,
  and register tables with DuckDB.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
import pyarrow.dataset as pads

from . import clocks, duck
from .errors import RegistryFault, RegistryUnavailable, ResourceNotFoundError
from .location import Located, Location, Resolution, Rewrite, Sources, resolve_sources
from .manifest import Manifest, RegistryBinding, Resource
from .predicates import Predicate, both, expression, on_clock_constraints
from .protocols import Memo
from .registries import acquire, held, hold, parse
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
    def resolution(self) -> Resolution:
        """The resolution documents ranked for this packet, and those not used (Part 04 §5.5)."""
        return self._root.resolution

    def locate(self, resource_id: str) -> Located:
        """Where one resource's bytes are, and the documents whose source and mirror placed them.

        Raises
        ------
        ResourceNotFoundError
            If the manifest declares no such resource.
        UnresolvedSource
            If it names a source no ranked document locates for this reader.
        """
        resource = self.resource(resource_id)
        return self._root.locate(resource.uri, resource.source)

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

    def contents(
        self,
        *,
        content_class: str | None = None,
        kind: str | None = None,
        stored: bool = True,
    ) -> pa.Table:
        """List what each resource holds: a row per table column, and one per other resource.

        A declaration names the columns a table may hold, and only its Parquet footer says which
        it does. The footers are read at once, so over a store the listing costs about one round
        trip rather than one per table. An array's shape and dtype are left to
        :meth:`array_resource`, which reads its metadata document.

        Parameters
        ----------
        content_class : str, optional
            Restrict to one content class, e.g. ``core``.
        kind : str, optional
            Restrict to one kind, e.g. ``table``.
        stored : bool, default True
            List the columns each table stores, from its footer. False lists the columns its
            declaration allows, with their declared types, from the bound registries alone, so
            it reads no table but may name an optional column a table omits.

        Returns
        -------
        pyarrow.Table
            `resource_id` and `kind`, and a column's `name` and `type`, null for a resource that
            is not a table: the stored Arrow type, or with `stored` False the declared one.
        """

        def held(resource: Resource) -> list[dict[str, Any]]:
            row = {"resource_id": resource.resource_id, "kind": resource.kind}
            if resource.kind == "table" and not stored:
                declared = (resource.declaration or {}).get("table", {}).get("columns", [])
                return [{**row, "name": column["name"], "type": column["type"]} for column in declared] or [row]
            if resource.kind == "table":
                schema = self.table_resource(resource.resource_id).schema()
                return [{**row, "name": field.name, "type": str(field.type)} for field in schema]
            return [row]

        wanted = self.resources(content_class=content_class, kind=kind)
        if not stored:
            return pa.Table.from_pylist([row for resource in wanted for row in held(resource)], schema=_CONTENTS)
        with ThreadPoolExecutor(max(1, min(len(wanted), _LISTING_REQUESTS))) as pool:
            rows = [row for rows in pool.map(held, wanted) for row in rows]
        return pa.Table.from_pylist(rows, schema=_CONTENTS)

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
        """One bound registry's document, whose SHA-256 equals its descriptor's.

        A document this process already holds under that digest answers without a request (Part 04
        §10); otherwise the stored copy is read and then held.

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
            If the manifest binds no such registry, or this process holds no document with its
            digest and the stored copy is missing, unreadable, or fails it (Part 04 §10).
        """
        if registry_id not in self._acquired:
            binding = self._manifest.registries.get(registry_id)
            if binding is None:
                raise RegistryUnavailable(registry_id, RegistryFault.MISSING, "the manifest binds no such registry")
            document = held(binding.sha256)
            if document is None:
                self._fetch_unheld()
                document = self._acquired.get(registry_id) or acquire(self._root, binding)
                hold(document)
            self._acquired[registry_id] = document
        return self._acquired[registry_id]

    def _fetch_unheld(self) -> None:
        """Read every bound registry this process does not hold at once, so the round trips overlap.

        A copy that cannot be read is left for :meth:`registry_bytes` to read again and report, so
        only an operation needing that registry fails.
        """
        unheld = [
            (name, binding)
            for name, binding in self._manifest.registries.items()
            if name not in self._acquired and held(binding.sha256) is None
        ]
        if len(unheld) < 2:
            return

        def read(binding: RegistryBinding) -> bytes | None:
            try:
                return acquire(self._root, binding)
            except RegistryUnavailable:
                return None

        with ThreadPoolExecutor(len(unheld)) as pool:
            for (name, _), document in zip(unheld, pool.map(read, (b for _, b in unheld)), strict=True):
                if document is not None:
                    hold(document)
                    self._acquired[name] = document

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


#: Footers :meth:`Packet.contents` reads at once.
_LISTING_REQUESTS = 32

_CONTENTS = pa.schema(
    [
        pa.field("resource_id", pa.string(), nullable=False),
        pa.field("kind", pa.string()),
        pa.field("name", pa.string()),
        pa.field("type", pa.string()),
    ]
)


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
        The caller's mirrors (Part 04 §5.5.1): mirror prefix to the location standing for it,
        ranked before every document. A committed packet records where its writer reached each
        resource, so this is how the same bytes are reached from somewhere else without editing
        the packet. The longest prefix wins, and a location relative to the root is never mirrored.
    sources : iterable, optional
        Source resolution documents, as mappings of source name to URI or as locations to read,
        ranked after `rewrite` in the order given and before the configuration's
        (:data:`~escapewheel_reader.location.SOURCES_ENVIRONMENT`) and the packet root's own
        `sources.json`. A location whose document is absent, fails the schema or declares an
        unknown version is refused.

    Returns
    -------
    Packet
        The opened packet.
    """
    root = Location.of(path)
    return Packet(Location.of(root, resolve_sources(root, sources, rewrite)), Manifest.load(root))


if TYPE_CHECKING:  # pragma: no cover
    # Checked statically: a `Packet` is what `PacketLike` describes.
    _PACKET_LIKE: type[PacketLike] = Packet

__all__ = ["Packet", "open_packet"]
