"""Handles that read a resource the manifest declares.

- :class:`TableResource` -- read a table into Arrow, scan it lazily in Arrow or Polars, or register
  it with DuckDB.
- :class:`ArrayResource` -- an array's shape, chunking and codecs without Zarr, and its values with
  Zarr.
- :data:`ZARR_METADATA_FILENAMES` -- the metadata document's name in each Zarr format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
import pyarrow.dataset as pads
import pyarrow.parquet as pq

from .errors import ResourceUnreadableError, UnresolvedSource, UnsupportedCodecError
from .location import Location
from .manifest import Resource
from .profile import variant_for_zarr_format, zarr_floor_admits
from .sql import sql_name

if TYPE_CHECKING:  # pragma: no cover
    import duckdb
    import polars as pl


#: Where a Zarr array keeps its metadata, by format version. v3 names it `zarr.json`; v2, which
#: Part 03 §6.1 permits an external array to use, names it `.zarray`. Both are JSON.
ZARR_METADATA_FILENAMES: dict[Literal[2, 3], str] = {3: "zarr.json", 2: ".zarray"}


def _locate(resource: Resource, root: Location) -> Location:
    """Where a declared resource's bytes are, naming the resource when its URI names no place."""
    try:
        return root.resolve(resource.uri, resource.source)
    except UnresolvedSource as exc:
        exc.resource_id = resource.resource_id
        raise
    except ResourceUnreadableError as exc:
        raise ResourceUnreadableError(
            f"{resource.resource_id}: {exc}", resource_id=resource.resource_id, source=resource.source
        ) from exc


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
    where = _locate(resource, root)
    if not where.is_local:
        # A store only a library with that backend can open, which `store` hands over as the
        # URI itself.
        raise ResourceUnreadableError(
            f"{resource.resource_id}: {where} is {where.scheme}:, which has no local path; "
            "open it through a store that speaks that scheme",
            resource_id=resource.resource_id,
            source=resource.source,
        )
    resolved = where.path
    if not resolved.exists():
        raise ResourceUnreadableError(
            f"{resource.resource_id}: {resource.uri} does not resolve under {root}",
            resource_id=resource.resource_id,
            source=resource.source,
        )
    return resolved


def _store(resource: Resource, root: Location) -> str:
    """Return what to hand a Zarr store: the URI itself when remote, else the resolved path.

    An external array is expected to be the large one (Part 04 §5.1), and in production that means
    an object store rather than a filesystem. Zarr opens such a URI directly given a backend
    for it, so resolving to a `Path` first would be the thing that made it unopenable.
    """
    where = _locate(resource, root)
    if not where.is_local:
        return where.uri
    return str(_resolve(resource, root))


def _unknown_codec_errors() -> tuple[type[Exception], ...]:
    """Return what Zarr raises for a codec it has no implementation of, v3 and v2 alike.

    Caught by class rather than as any failure to open, so malformed metadata is not reported as a
    missing codec. zarr-python before 3.1.3 raises a bare `KeyError` instead, which is not caught.
    """
    import numcodecs.errors
    import zarr.errors

    found = (getattr(zarr.errors, "UnknownCodecError", None), getattr(numcodecs.errors, "UnknownCodecError", None))
    return tuple(error for error in found if error is not None)


class TableResource:
    """A tabular resource bound to a packet root.

    The portable profile represents each table as one Parquet object.
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
        return _locate(self._resource, self._root)

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

        **Credentials are the caller's, deliberately.** Part 04 §5.1 makes reachability a property
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
            raise ResourceUnreadableError(f"{self.resource_id}: {exc}", resource_id=self.resource_id) from exc

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
        connection.sql(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM '{base}'")
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
        frame: pl.LazyFrame = _pl.scan_parquet(base)
        return frame


class ArrayResource:
    """A dense array resource bound to a packet root.

    Metadata and values have different costs, and this class keeps them apart. A Zarr array's
    metadata is a JSON document in the store, so shape, dtype, chunking, fill value and codecs
    are all answerable with no Zarr library present -- which is what lets a validator check
    Part 04 §5.3's level 2 without taking a dependency on the thing it is checking. Only
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
        return _locate(self._resource, self._root)

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
        an object store (Part 04 §5.1).

        Returns
        -------
        str
            A URI for a remote store, or the resolved local path.
        """
        return _store(self._resource, self._root)

    @property
    def zarr_format(self) -> Literal[2, 3]:
        """Which Zarr version the store actually uses, 3 or 2.

        Read from format-owned metadata rather than a packet claim.

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
        for version, name in ZARR_METADATA_FILENAMES.items():
            if where.join(name).exists():
                return version
        raise ResourceUnreadableError(
            f"{self.resource_id}: {where} holds no Zarr metadata document", resource_id=self.resource_id
        )

    @property
    def _is_local(self) -> bool:
        """Whether the array's bytes are reachable as a filesystem path."""
        return self.location.is_local

    def metadata(self) -> dict[str, Any]:
        """Read and parse the array's own Zarr metadata document.

        A remote array is read through Zarr, which needs the ``arrays`` extra and a backend for
        the URI's scheme. A local one is the JSON document itself, so shape, dtype, chunking
        and codecs cost nothing and need no library at all -- which is the property Part 03 §6.5
        protects and the reason `arrays` is an extra in the first place.

        Returns
        -------
        dict
            The parsed document, read once and kept.
        """
        if self._metadata is None:
            parsed = self._read_document()
            self._metadata = parsed if parsed is not None else dict(self.open().metadata.to_dict())
        return self._metadata

    def _read_document(self) -> dict[str, Any] | None:
        """Parse the metadata document directly, or return None where only Zarr can reach it."""
        document = self.location.join(ZARR_METADATA_FILENAMES[self.zarr_format])
        try:
            parsed: dict[str, Any] = json.loads(document.read_bytes())
        except Exception:  # noqa: BLE001 - a store this cannot read is Zarr's problem, not an error
            return None
        return parsed

    @property
    def shape(self) -> tuple[int, ...]:
        """The array's shape, in stored axis order (Part 03 §6.2)."""
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
        """The value an unwritten chunk reads as. Part 03 §6.1 requires one to be declared."""
        return self.metadata().get("fill_value")

    @property
    def codecs(self) -> tuple[str, ...]:
        """The codec pipeline by name, in stored order, ``bytes`` included.

        A sharded v3 array's pipeline is the sharding codec alone; the pipeline inside each shard
        is part of that codec's configuration in :meth:`metadata`. A v2 array's is its filters,
        then its compressor.
        """
        meta = self.metadata()
        if self.zarr_format == 3:
            return tuple(codec if isinstance(codec, str) else str(codec["name"]) for codec in meta.get("codecs", ()))
        stages = [*(meta.get("filters") or ()), meta.get("compressor")]
        return tuple(str(stage["id"]) for stage in stages if stage)

    @property
    def within_reader_floor(self) -> bool:
        """Whether the array lies within its Zarr variant's reader floor (Part 03 §6.4).

        Outside it the array is valid but beyond the portability guarantee (Part 03 §2):
        this reader may decode it, and a conforming one need not.
        """
        return self._admitted(self.metadata())

    def _admitted(self, document: dict[str, Any]) -> bool:
        """Whether the descriptor's floor for this array's Zarr version admits its metadata."""
        variant = variant_for_zarr_format(self.zarr_format)
        return variant is not None and zarr_floor_admits(document, variant["reader_floor"])

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
        UnsupportedCodecError
            If Zarr cannot decode a codec the array uses.
        """
        if self._array is None:
            try:
                import zarr
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise ImportError("reading array values requires zarr; install the 'arrays' extra") from exc
            try:
                self._array = zarr.open_array(self.store, mode="r", zarr_format=self.zarr_format)
            except _unknown_codec_errors() as exc:
                # Not `metadata()`: where only Zarr reaches the store it would reopen, and fail, forever.
                document = self._metadata if self._metadata is not None else self._read_document()
                outside = None if document is None else not self._admitted(document)
                floor = {None: "unassessed", True: "outside it", False: "within it"}[outside]
                raise UnsupportedCodecError(
                    self.resource_id, f"{exc} (reader floor: {floor})", outside_floor=outside
                ) from exc
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
