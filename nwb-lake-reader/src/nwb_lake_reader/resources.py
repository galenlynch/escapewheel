"""Readable handles for the resources a manifest declares.

A :class:`~nwb_lake_reader.manifest.Resource` records what the manifest says. The classes
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
from urllib.parse import unquote, urlparse

import pyarrow as pa
import pyarrow.dataset as pads
import pyarrow.parquet as pq

from .errors import ResourceUnreadableError
from .manifest import Resource
from .sql import sql_name

if TYPE_CHECKING:  # pragma: no cover
    import duckdb
    import polars as pl


#: Arrow types a Parquet dictionary decodes to. Only these are worth asking back as
#: dictionaries; a numeric column gains nothing and an index would cost more than the value.
_DICTIONARY_TYPES = ("string", "large_string", "binary", "large_binary")

#: Where a Zarr array keeps its metadata. v3 names it `zarr.json`; v2, which R21 §3 permits
#: an external array to use, names it `.zarray`. Both are JSON.
#:
#: `physical_profile` -> Zarr version, for a remote array whose documents cannot be read
#: without a backend for its scheme (R21 §3.2).
_ZARR_PROFILES: dict[str, Literal[2, 3]] = {"zarr_v2": 2, "zarr_v3": 3}
_ZARR_METADATA: dict[Literal[2, 3], str] = {3: "zarr.json", 2: ".zarray"}


def _resolve(resource: Resource, root: Path) -> Path:
    """Resolve a declared URI against the packet root.

    Parameters
    ----------
    resource : Resource
        The manifest entry.
    root : Path
        Packet root directory.

    Returns
    -------
    Path
        The resolved path.

    Raises
    ------
    ResourceUnreadableError
        If the URI names a store this cannot open locally, or the path does not exist.
    """
    scheme = urlparse(resource.uri).scheme
    if scheme and scheme != "file" and len(scheme) > 1:
        # A single-letter scheme is a Windows drive, not a URI. Anything else is a store only
        # a library with that backend can open, which `store` hands over as the URI itself.
        raise ResourceUnreadableError(
            f"{resource.resource_id}: {resource.uri} is {scheme}:, which has no local path; "
            "open it through a store that speaks that scheme"
        )
    declared = Path(unquote(urlparse(resource.uri).path)) if scheme == "file" else Path(resource.uri)
    resolved = declared if declared.is_absolute() else root / declared
    if not resolved.exists():
        raise ResourceUnreadableError(f"{resource.resource_id}: {resource.uri} does not resolve under {root}")
    return resolved


def _store(resource: Resource, root: Path) -> str:
    """Return what to hand a Zarr store: the URI itself when remote, else the resolved path.

    An external array is expected to be the large one (R14 §2.3), and in production that means
    an object store rather than a filesystem. Zarr opens such a URI directly given a backend
    for it, so resolving to a `Path` first would be the thing that made it unopenable.
    """
    scheme = urlparse(resource.uri).scheme
    if scheme and scheme != "file" and len(scheme) > 1:
        return resource.uri
    return str(_resolve(resource, root))


def _codec_names(codecs: Iterable[Mapping[str, Any]]) -> list[str]:
    """Flatten a Zarr v3 codec pipeline to names, outermost first.

    The mandatory `bytes` codec is dropped, matching what a manifest declares (R15 §2). A
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

    def __init__(self, resource: Resource, root: Path) -> None:
        """Bind a declared resource to the packet root that contains it.

        Parameters
        ----------
        resource : Resource
            The manifest entry.
        root : Path
            Packet root directory.
        """
        self._resource = resource
        self._root = root

    @property
    def resource(self) -> Resource:
        """The underlying manifest entry."""
        return self._resource

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

    def dictionary_columns(self) -> list[str]:
        """Columns the file stores dictionary-encoded, and so can return without decoding.

        Parquet writes a low-cardinality column as small integer indices into a dictionary
        held once per row group. Asking for the values decodes those indices back into one
        string per row, which for an identity column repeated over every row of a large table
        is the dominant cost of reading it: measured on 20 M spikes, the five identity columns
        of `core.spike_events` are 0.40 GB read as dictionaries and 4.38 GB decoded, 0.08 s
        against 0.67 s. On disk they are 9.4 MB for 287 M rows.

        Only columns the writer actually dictionary-encoded are named. Requesting a dictionary
        for a column stored some other way makes Arrow build one during the read, which for a
        high-cardinality column costs more than the strings it replaces.

        Returns
        -------
        list of str
            Column names, in schema order. Empty when the resource is partitioned, since the
            fragments need not agree on encoding.
        """
        if self._resource.is_partitioned:
            return []
        try:
            metadata = pq.ParquetFile(self.path).metadata
        except Exception:  # noqa: BLE001 - an unreadable file is reported by the caller
            return []
        if not metadata.num_row_groups:
            return []
        schema = metadata.schema.to_arrow_schema()
        group = metadata.row_group(0)
        named = []
        for index in range(group.num_columns):
            column = group.column(index)
            name = column.path_in_schema
            if name not in schema.names or str(schema.field(name).type) not in _DICTIONARY_TYPES:
                continue
            if "RLE_DICTIONARY" in column.encodings or "PLAIN_DICTIONARY" in column.encodings:
                named.append(name)
        return named

    def to_arrow(self, *, columns: list[str] | None = None, decode: bool = True) -> pa.Table:
        """Read the resource into memory, in stored order.

        Parameters
        ----------
        columns : list of str, optional
            Read only these columns. Projection is not a filter: it goes straight to the
            Parquet reader, which never touches the column chunks left out.
        decode : bool, default True
            Return plain strings, which is what a caller expects and what everything
            downstream already handles. Pass False to keep the columns as
            `dictionary<string, int32>`, the form the file stores.

            That is worth reaching for only when reading a whole identity column, which is
            the one case where decoding dominates: `unit_id` over 287 M spikes is 0.23 s and
            1.15 GB kept against 2.29 s and 12.75 GB decoded, and the decoded read needs
            13.6 GB of memory to complete at all. Filtered reads never approach it, so the
            default stays the predictable one rather than the fast one.

        Returns
        -------
        pyarrow.Table
            The table.
        """
        if self._resource.is_partitioned:
            return self.dataset(decode=decode).to_table(columns=columns)
        if decode:
            return pq.read_table(self.path, columns=columns)
        wanted = self.dictionary_columns()
        if columns is not None:
            wanted = [name for name in wanted if name in columns]
        return pq.read_table(self.path, columns=columns, read_dictionary=wanted or None)

    def dataset(self, *, decode: bool = True) -> pads.Dataset:
        """Open the resource as a PyArrow dataset without reading it.

        Parameters
        ----------
        decode : bool, default True
            The opposite default to :meth:`to_arrow`, and measured rather than assumed. A
            filtered scan returns few rows, so the strings it decodes are cheap -- but the
            dictionaries are per row group, and reconciling 1,891 of them costs far more than
            the decoding it saves: 1.3 s against 0.037 s selecting 24 units, and 1.7 s against
            0.033 s selecting one. A whole-file read is the reverse, which is why `to_arrow`
            defaults the other way.

        Returns
        -------
        pyarrow.dataset.Dataset
            A lazy dataset, suitable for predicate pushdown over large resources.
        """
        columns = [] if decode else self.dictionary_columns()
        options = pads.ParquetReadOptions(dictionary_columns=columns) if columns else None
        fmt = pads.ParquetFileFormat(read_options=options) if options else pads.ParquetFileFormat()
        return pads.dataset(self.path, format=fmt, partitioning="hive")

    def schema(self) -> pa.Schema:
        """Read the resource's Arrow schema without reading its data.

        Returns
        -------
        pyarrow.Schema
            The schema.
        """
        if self._resource.is_partitioned:
            return self.dataset().schema
        return pq.read_schema(self.path)

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
        target = f"{self.path}/**/*.parquet" if self._resource.is_partitioned else str(self.path)
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
        target = f"{self.path}/**/*.parquet" if self._resource.is_partitioned else str(self.path)
        frame: pl.LazyFrame = _pl.scan_parquet(target)
        return frame


class ArrayResource:
    """A dense array resource bound to a packet root.

    Metadata and values have different costs, and this class keeps them apart. A Zarr array's
    metadata is a JSON document in the store, so shape, dtype, chunking, fill value and codecs
    are all answerable with no Zarr library present -- which is what lets a validator check
    R15 §4's level 2 without taking a dependency on the thing it is checking. Only
    :meth:`read` needs Zarr, behind the ``arrays`` extra.
    """

    def __init__(self, resource: Resource, root: Path) -> None:
        """Bind a declared array resource to the packet root that contains it.

        Parameters
        ----------
        resource : Resource
            The manifest entry.
        root : Path
            Packet root directory.
        """
        self._resource = resource
        self._root = root
        self._metadata: dict[str, Any] | None = None
        self._array: Any = None

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
        an object store (R14 §2.3).

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
        is what R15 §4's level 2 checks, so taking the manifest's word would make the check
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
        if not self._is_local:
            # The manifest's word, and only here. Taking it for a packet-owned array would
            # make R15 §4's level 2 compare a value with itself; for a remote external one
            # there is nothing local to compare against, and R14 §2.3.1 already frames the
            # declaration as a claim rather than a verified fact.
            declared = str(self._resource.entry.get("physical_profile", ""))
            if declared in _ZARR_PROFILES:
                return _ZARR_PROFILES[declared]
            raise ResourceUnreadableError(
                f"{self.resource_id}: {self._resource.uri} is remote and declares no Zarr version"
            )
        root = self.path
        for version, name in _ZARR_METADATA.items():
            if (root / name).is_file():
                return version
        raise ResourceUnreadableError(f"{self.resource_id}: {root} holds no Zarr metadata document")

    @property
    def _is_local(self) -> bool:
        """Whether the array's bytes are reachable as a filesystem path."""
        scheme = urlparse(self._resource.uri).scheme
        return not scheme or scheme == "file" or len(scheme) == 1

    def metadata(self) -> dict[str, Any]:
        """Read and parse the array's own Zarr metadata document.

        A remote array is read through Zarr, which needs the ``arrays`` extra and a backend for
        the URI's scheme. A local one is the JSON document itself, so shape, dtype, chunking
        and codecs cost nothing and need no library at all -- which is the property R3 §2.1
        protects and the reason `arrays` is an extra in the first place.

        Returns
        -------
        dict
            The parsed document, read once and kept.
        """
        if self._metadata is None:
            if self._is_local:
                parsed: dict[str, Any] = json.loads((self.path / _ZARR_METADATA[self.zarr_format]).read_text())
            else:
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
        """The value an unwritten chunk reads as. R3 §7.1 requires one to be declared."""
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
                scheme = urlparse(self._resource.uri).scheme or "file"
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
