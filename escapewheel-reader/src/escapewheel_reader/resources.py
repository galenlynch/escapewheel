"""Readable handles for the resources a manifest declares.

A :class:`~escapewheel_reader.manifest.Resource` records what the manifest says. The classes
here bind one to a packet root and read it.

:class:`TableResource` needs PyArrow. :class:`ArrayResource` needs nothing at all to answer
what an array is -- a Zarr array declares its shape, chunking and codecs in a JSON document
beside the chunks -- and Zarr only to read values. The array path costs what it uses, the way
DuckDB does behind the `sql` extra.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
import pyarrow.dataset as pads
import pyarrow.parquet as pq

from .errors import ResourceUnreadableError
from .location import Location
from .manifest import Resource
from .sql import sql_name

if TYPE_CHECKING:  # pragma: no cover
    import duckdb
    import polars as pl


#: Where a Zarr array keeps its metadata. v3 names it `zarr.json`; v2, which R21 §3 permits
#: an external array to use, names it `.zarray`. Both are JSON.
#:
#: `physical_profile` -> Zarr version, for a remote array whose documents cannot be read
#: without a backend for its scheme (`03` §6.1).
_ZARR_PROFILES: dict[str, Literal[2, 3]] = {"zarr_v2": 2, "zarr_v3": 3}
_ZARR_METADATA: dict[Literal[2, 3], str] = {3: "zarr.json", 2: ".zarray"}


def _resolve(resource: Resource, root: Location) -> Path:
    """Resolve a declared URI to a local filesystem path.

    Parameters
    ----------
    resource : Resource
        The manifest entry.
    root : Location
        Packet root.

    Returns
    -------
    Path
        The resolved path.

    Raises
    ------
    ResourceUnreadableError
        If the URI names a store this cannot open locally, or the path does not exist.
    """
    where = root.resolve(resource.uri, resource.source)
    if not where.is_local:
        # A store only a library with that backend can open, which `store` hands over as the
        # URI itself.
        raise ResourceUnreadableError(
            f"{resource.resource_id}: {where} is {where.scheme}:, which has no local path; "
            "open it through a store that speaks that scheme"
        )
    resolved = where.path
    if not resolved.exists():
        raise ResourceUnreadableError(f"{resource.resource_id}: {resource.uri} does not resolve under {root}")
    return resolved


def _store(resource: Resource, root: Location) -> str:
    """Return what to hand a Zarr store: the URI itself when remote, else the resolved path.

    An external array is expected to be the large one (`04` §5.1), and in production that means
    an object store rather than a filesystem. Zarr opens such a URI directly given a backend
    for it, so resolving to a `Path` first would be the thing that made it unopenable.
    """
    where = root.resolve(resource.uri, resource.source)
    if not where.is_local:
        return where.uri
    return str(_resolve(resource, root))


def _codec_names(codecs: Iterable[Mapping[str, Any]]) -> list[str]:
    """Flatten a Zarr v3 codec pipeline to names, outermost first.

    The mandatory `bytes` codec is dropped, matching what a manifest declares (`03` §6.4). A
    sharding codec is reported together with the codecs nested inside it, because reading one
    chunk needs all of them.

    Parameters
    ----------
    codecs : iterable of Mapping
        The `codecs` array from a Zarr v3 metadata document.

    Returns
    -------
    list of str
        Codec names.
    """
    names = []
    for codec in codecs:
        name = str(codec.get("name", ""))
        if name and name != "bytes":
            names.append(name)
        if nested := codec.get("configuration", {}).get("codecs"):
            names.extend(_codec_names(nested))
    return names


class TableResource:
    """A tabular resource bound to a packet root.

    Handles single-file and partitioned resources identically; which one a packet uses is
    declared in the manifest and is not the caller's concern.
    """

    def __init__(self, resource: Resource, root: Location | Path | str) -> None:
        """Bind a declared resource to the packet root that contains it.

        Parameters
        ----------
        resource : Resource
            The manifest entry.
        root : Location, Path, or str
            Packet root: a local directory or a store prefix.
        """
        self._resource = resource
        self._root = Location.of(root)

    @property
    def resource(self) -> Resource:
        """The underlying manifest entry."""
        return self._resource

    @property
    def location(self) -> Location:
        """Where this resource's bytes are, after the root, any source, and any substitution."""
        return self._root.resolve(self._resource.uri, self._resource.source)

    @property
    def resource_id(self) -> str:
        """The dotted resource ID."""
        return self._resource.resource_id

    @property
    def sql_name(self) -> str:
        """The name this resource takes when registered with a SQL engine."""
        return sql_name(self._resource.resource_id)

    def __repr__(self) -> str:
        """Return a representation naming the resource and its URI."""
        return f"<TableResource {self.resource_id!r} at {self._resource.uri}>"

    @property
    def path(self) -> Path:
        """Resolve the resource's URI to a filesystem path.

        Returns
        -------
        Path
            The resolved path.

        Raises
        ------
        ResourceUnreadableError
            If the path does not exist.
        """
        return _resolve(self._resource, self._root)

    def _store(self) -> tuple[Any, Any]:
        """Where the bytes are, and the filesystem that reaches them.

        Local resolves to a path and no filesystem, which is what every pyarrow entry point
        already takes. A store URI goes through `pyarrow.fs`, which pyarrow ships -- reading a
        remote table needs no dependency the read path did not already have.

        **Credentials are the caller's, deliberately.** `04` §5.1 makes reachability a property
        of the reader's situation rather than of the packet, so this takes whatever the
        filesystem's own default chain finds and never configures one.

        Raises
        ------
        ResourceUnreadableError
            If the URI names a scheme pyarrow cannot open.
        """
        if self.is_local:
            return self.path, None
        try:
            return self.location.store()
        except ResourceUnreadableError as exc:
            raise ResourceUnreadableError(f"{self.resource_id}: {exc}") from exc

    def to_arrow(self, *, columns: list[str] | None = None) -> pa.Table:
        """Read the resource into memory, in stored order.

        Parameters
        ----------
        columns : list of str, optional
            Read only these columns. Projection is not a filter: it goes straight to the
            Parquet reader, which never touches the column chunks left out.

        Returns
        -------
        pyarrow.Table
            The table, with strings decoded. Parquet stores a low-cardinality column as codes
            into a dictionary and this decodes them, which is what a caller expects and what
            everything downstream handles.
        """
        if self._resource.is_partitioned:
            return self.dataset().to_table(columns=columns)
        path, filesystem = self._store()
        return pq.read_table(path, columns=columns, filesystem=filesystem)

    def dataset(self) -> pads.Dataset:
        """Open the resource as a PyArrow dataset without reading it.

        Returns
        -------
        pyarrow.dataset.Dataset
            A lazy dataset, suitable for predicate pushdown over large resources.
        """
        path, filesystem = self._store()
        opened: pads.Dataset = pads.dataset(
            path, format=pads.ParquetFileFormat(), partitioning="hive", filesystem=filesystem
        )
        return opened

    def schema(self) -> pa.Schema:
        """Read the resource's Arrow schema without reading its data.

        Returns
        -------
        pyarrow.Schema
            The schema.
        """
        if self._resource.is_partitioned:
            return self.dataset().schema
        path, filesystem = self._store()
        return pq.read_schema(path, filesystem=filesystem)

    @property
    def is_local(self) -> bool:
        """Whether the resource resolves to a filesystem path rather than a store URI.

        A relative URI follows the packet root, so the same packet is local on disk and remote
        in a store without either resource entry changing.
        """
        return self.location.is_local

    def register(self, connection: duckdb.DuckDBPyConnection, *, name: str | None = None) -> str:
        """Register the resource as a view on a DuckDB connection.

        Parameters
        ----------
        connection : duckdb.DuckDBPyConnection
            The connection to register into.
        name : str, optional
            View name. Defaults to the flattened resource ID.

        Returns
        -------
        str
            The view name used.
        """
        view = name or self.sql_name
        # A remote table is handed over as its URI: DuckDB reads an object store through its own
        # client, so resolving to a local path first is the thing that would make it unreadable.
        base = str(self.path) if self.is_local else self.location.uri
        target = f"{base}/**/*.parquet" if self._resource.is_partitioned else base
        connection.sql(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM '{target}'")
        return view

    def scan_polars(self) -> pl.LazyFrame:
        """Open the resource as a Polars lazy frame.

        Polars is an optional dependency; install it with the ``polars`` extra.

        Returns
        -------
        polars.LazyFrame
            A lazy scan over the resource.

        Raises
        ------
        ImportError
            If Polars is not installed.
        """
        try:
            import polars as _pl
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise ImportError("scan_polars requires polars; install the 'polars' extra") from exc
        base = str(self.path) if self.is_local else self.location.uri
        target = f"{base}/**/*.parquet" if self._resource.is_partitioned else base
        frame: pl.LazyFrame = _pl.scan_parquet(target)
        return frame


class ArrayResource:
    """A dense array resource bound to a packet root.

    Metadata and values have different costs, and this class keeps them apart. A Zarr array's
    metadata is a JSON document in the store, so shape, dtype, chunking, fill value and codecs
    are all answerable with no Zarr library present -- which is what lets a validator check
    `04` §5.3's level 2 without taking a dependency on the thing it is checking. Only
    :meth:`read` needs Zarr, behind the ``arrays`` extra.
    """

    def __init__(self, resource: Resource, root: Location | Path | str) -> None:
        """Bind a declared array resource to the packet root that contains it.

        Parameters
        ----------
        resource : Resource
            The manifest entry.
        root : Location, Path, or str
            Packet root: a local directory or a store prefix.
        """
        self._resource = resource
        self._root = Location.of(root)
        self._metadata: dict[str, Any] | None = None
        self._array: Any = None

    @property
    def location(self) -> Location:
        """Where this array's bytes are, after the root, any source, and any substitution."""
        return self._root.resolve(self._resource.uri, self._resource.source)

    @property
    def resource(self) -> Resource:
        """The underlying manifest entry."""
        return self._resource

    @property
    def resource_id(self) -> str:
        """The dotted resource ID."""
        return self._resource.resource_id

    def __repr__(self) -> str:
        """Return a representation naming the resource and its URI."""
        return f"<ArrayResource {self.resource_id!r} at {self._resource.uri}>"

    @property
    def path(self) -> Path:
        """Resolve the resource's URI to a filesystem path.

        Returns
        -------
        Path
            The resolved path.

        Raises
        ------
        ResourceUnreadableError
            If the path does not exist.
        """
        return _resolve(self._resource, self._root)

    @property
    def store(self) -> str:
        """What to hand a Zarr store, which for a remote array is its URI rather than a path.

        `path` is the local answer and raises for a scheme it cannot reach. This is the one to
        pass on: an external array is expected to be the large one, and in production that is
        an object store (`04` §5.1).

        Returns
        -------
        str
            A URI for a remote store, or the resolved local path.
        """
        return _store(self._resource, self._root)

    @property
    def zarr_format(self) -> Literal[2, 3]:
        """Which Zarr version the store actually uses, 3 or 2.

        Read from the store, never from the manifest's ``physical_profile``: the two agreeing
        is what `04` §5.3's level 2 checks, so taking the manifest's word would make the check
        compare a value with itself.

        Returns
        -------
        int
            3 or 2.

        Raises
        ------
        ResourceUnreadableError
            If neither metadata document is present.
        """
        where = self.location
        if self._resource.is_external:
            # The manifest's word, and only here. `03` §8 frames an external resource's
            # declaration as a claim rather than a verified fact, and there is nothing the
            # packet owns to compare it against.
            declared = str(self._resource.entry.get("physical_profile", ""))
            if declared in _ZARR_PROFILES:
                return _ZARR_PROFILES[declared]
            raise ResourceUnreadableError(f"{self.resource_id}: {where} is external and declares no Zarr version")
        # A packet-owned array is read from the store whether that store is a disk or a
        # bucket: taking the manifest's word would make `04` §5.3's level 2 compare a value with
        # itself, and where the packet sits does not change what the check is for.
        for version, name in _ZARR_METADATA.items():
            if where.join(name).exists():
                return version
        raise ResourceUnreadableError(f"{self.resource_id}: {where} holds no Zarr metadata document")

    @property
    def _is_local(self) -> bool:
        """Whether the array's bytes are reachable as a filesystem path."""
        return self.location.is_local

    def metadata(self) -> dict[str, Any]:
        """Read and parse the array's own Zarr metadata document.

        A remote array is read through Zarr, which needs the ``arrays`` extra and a backend for
        the URI's scheme. A local one is the JSON document itself, so shape, dtype, chunking
        and codecs cost nothing and need no library at all -- which is the property `03` §5.5
        protects and the reason `arrays` is an extra in the first place.

        Returns
        -------
        dict
            The parsed document, read once and kept.
        """
        if self._metadata is None:
            document = self.location.join(_ZARR_METADATA[self.zarr_format])
            try:
                parsed: dict[str, Any] = json.loads(document.read_bytes())
            except Exception:  # noqa: BLE001 - a store this cannot read is Zarr's problem, not an error
                parsed = dict(self.open().metadata.to_dict())
            self._metadata = parsed
        return self._metadata

    @property
    def shape(self) -> tuple[int, ...]:
        """The array's shape, in stored axis order (R3 §5)."""
        return tuple(int(n) for n in self.metadata()["shape"])

    @property
    def dtype(self) -> str:
        """The array's data type, spelled as Zarr spells it."""
        meta = self.metadata()
        return str(meta["data_type"] if self.zarr_format == 3 else meta["dtype"])

    @property
    def chunks(self) -> tuple[int, ...]:
        """The unit of a read: the inner chunk where the array is sharded, the grid otherwise."""
        meta = self.metadata()
        if self.zarr_format == 2:
            return tuple(int(n) for n in meta["chunks"])
        for codec in meta.get("codecs", ()):
            if codec.get("name") == "sharding_indexed":
                return tuple(int(n) for n in codec["configuration"]["chunk_shape"])
        return tuple(int(n) for n in meta["chunk_grid"]["configuration"]["chunk_shape"])

    @property
    def shards(self) -> tuple[int, ...] | None:
        """The unit of one object where the array is sharded, None where it is not.

        Sharding is what lets the chunk be the unit of the question without making one file
        per chunk, which against object storage is one request per chunk.
        """
        meta = self.metadata()
        if self.zarr_format == 2:
            return None
        if not any(codec.get("name") == "sharding_indexed" for codec in meta.get("codecs", ())):
            return None
        return tuple(int(n) for n in meta["chunk_grid"]["configuration"]["chunk_shape"])

    @property
    def fill_value(self) -> Any:
        """The value an unwritten chunk reads as. `03` §6.1 requires one to be declared."""
        return self.metadata().get("fill_value")

    @property
    def codecs(self) -> tuple[str, ...]:
        """Every codec the array actually uses, outermost first, excluding ``bytes``.

        Comparable directly against :attr:`Resource.codecs`, which is what the manifest claims.
        """
        meta = self.metadata()
        if self.zarr_format == 3:
            return tuple(_codec_names(meta.get("codecs", ())))
        names = []
        if compressor := meta.get("compressor"):
            names.append(str(compressor["id"]))
        names.extend(str(f["id"]) for f in (meta.get("filters") or ()))
        return tuple(names)

    def open(self) -> Any:
        """Open the array for reading values, once, and keep it open.

        Held rather than reopened because opening is not free next to the read it enables:
        one unit of a sharded array costs 0.7 ms to read and 1.4 ms to reopen the store for,
        so a loop over units spends twice as long opening as reading.

        Zarr is an optional dependency; install it with the ``arrays`` extra. An array on an
        object store needs a backend for its scheme as well -- `s3fs` for `s3://` -- which
        Zarr resolves through fsspec and this package does not depend on either way.

        Returns
        -------
        zarr.Array
            The array, opened read-only.

        Raises
        ------
        ImportError
            If Zarr is not installed.
        """
        if self._array is None:
            try:
                import zarr
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise ImportError("reading array values requires zarr; install the 'arrays' extra") from exc
            try:
                self._array = zarr.open_array(self.store, mode="r", zarr_format=self.zarr_format)
            except ImportError as exc:  # pragma: no cover - depends on which backends are installed
                scheme = self.location.scheme or "file"
                raise ImportError(
                    f"{self.resource_id}: opening a {scheme}: store needs a backend for that scheme "
                    f"(s3fs for s3://, gcsfs for gs://); zarr resolves it through fsspec"
                ) from exc
        return self._array

    def read(self, selection: Any = ...) -> Any:
        """Read the array, or part of it, into memory.

        Parameters
        ----------
        selection : optional
            Any selection Zarr accepts. Defaults to the whole array. Prefer a selection
            aligned to :attr:`chunks`, which is the unit the store decompresses.

        Returns
        -------
        numpy.ndarray
            The values.
        """
        array = self.open()
        return array[...] if selection is ... else array[selection]
