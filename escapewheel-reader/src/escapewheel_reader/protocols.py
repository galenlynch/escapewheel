"""What a function taking a packet asks of it.

- :class:`PacketLike` -- the members of :class:`~escapewheel_reader.Packet` the free functions use.

A function typed against it accepts a :class:`~escapewheel_reader.Packet` or anything else that
resolves and reads resources the same way, such as a stand-in over in-memory tables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Collection

    import pyarrow as pa
    import pyarrow.dataset as pads

    # By name: inside the class body `duckdb` is the method.
    from duckdb import DuckDBPyConnection

    from .manifest import Resource
    from .packet import Predicate
    from .resources import ArrayResource, TableResource


class PacketLike(Protocol):
    """Resolution and reading of one packet's resources, as the free functions use them."""

    @property
    def registry(self) -> dict[str, Any]:
        """The core registry the packet binds."""

    def extensions(self) -> dict[str, dict[str, Any]]:
        """Every extension registry the packet binds, by registry ID."""

    def resources(
        self,
        *,
        content_class: str | None = None,
        layer: str | None = None,
        kind: str | None = None,
    ) -> tuple[Resource, ...]:
        """List declared resources, optionally filtered."""

    def resource(self, resource_id: str) -> Resource:
        """Look up one resource by ID."""

    def table_resource(self, resource_id: str) -> TableResource:
        """Get a readable handle for a table resource."""

    def array_resource(self, resource_id: str) -> ArrayResource:
        """Get a readable handle for a dense array resource."""

    def table(self, resource_id: str, *, columns: list[str] | None = None, **where: Predicate) -> pa.Table:
        """Read a table resource into memory, optionally narrowed."""

    def scan(self, resource_id: str) -> pads.Dataset:
        """Open a table resource lazily."""

    def duckdb(
        self,
        *,
        connection: DuckDBPyConnection | None = None,
        tables: Collection[str] | Literal["all"] | None = None,
        for_query: str | None = None,
    ) -> DuckDBPyConnection:
        """Register table resources as views and return the connection."""


__all__ = ["PacketLike"]
