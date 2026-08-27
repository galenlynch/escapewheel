"""Readable handles for the resources a manifest declares.

A :class:`~nwb_lake_reader.manifest.Resource` records what the manifest says. The classes
here bind one to a packet root and read it. ``ArrayResource`` arrives with Zarr support at
Phase 5 and should mirror this shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow.dataset as pads
import pyarrow.parquet as pq

from .errors import ResourceUnreadableError
from .manifest import Resource
from .sql import sql_name

if TYPE_CHECKING:  # pragma: no cover
    import duckdb
    import polars as pl
    import pyarrow as pa


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
        declared = Path(self._resource.uri)
        resolved = declared if declared.is_absolute() else self._root / declared
        if not resolved.exists():
            raise ResourceUnreadableError(
                f"{self.resource_id}: {self._resource.uri} does not resolve under {self._root}"
            )
        return resolved

    def to_arrow(self) -> pa.Table:
        """Read the resource into memory, in stored order.

        Returns
        -------
        pyarrow.Table
            The table.
        """
        if self._resource.is_partitioned:
            return self.dataset().to_table()
        return pq.read_table(self.path)

    def dataset(self) -> pads.Dataset:
        """Open the resource as a PyArrow dataset without reading it.

        Returns
        -------
        pyarrow.dataset.Dataset
            A lazy dataset, suitable for predicate pushdown over large resources.
        """
        return pads.dataset(self.path, format="parquet", partitioning="hive")

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
