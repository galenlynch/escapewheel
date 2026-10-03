"""What a function taking a packet asks of it.

- :class:`PacketLike` -- the members of :class:`~escapewheel_reader.Packet` the free functions use.
- :class:`Memo` -- what those functions have read from one packet and keep for its lifetime.
- :class:`PacketSetLike` -- what a transform or predicate asks of several packets.

A function typed against it accepts a :class:`~escapewheel_reader.Packet` or anything else that
resolves and reads resources the same way, such as a stand-in over in-memory tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Collection

    import numpy as np
    import pyarrow as pa
    import pyarrow.dataset as pads

    # By name: inside the class body `duckdb` is the method.
    from duckdb import DuckDBPyConnection
    from numpy.typing import NDArray

    from .clocks import ClockGraph
    from .manifest import Resource
    from .packet_set import Session
    from .predicates import Predicate
    from .resources import ArrayResource, TableResource
    from .runs import Ambiguity


@dataclass
class Memo:
    """What the free functions have read from one packet, kept for as long as the packet is.

    The packet owns it because each answer is a property of the packet's bytes, so nothing here
    is ever invalidated. A field is None, or `origins` lacks the key, until its function first
    answers.

    Attributes
    ----------
    anchors : dict or None
        :func:`~escapewheel_reader.clocks.anchors`: each clock's anchor ticks and their parents.
    clock_graph : ClockGraph or None
        :func:`~escapewheel_reader.clocks.clock_graph`: each clock's parent and alignment onto it.
    bound : float or None
        :func:`~escapewheel_reader.clocks.declared_bound`. Unset while the sessions table cannot
        be read.
    reference_clock : int or None
        :func:`~escapewheel_reader.clocks.reference_clock` with no session named.
    origins : dict
        :func:`~escapewheel_reader.clocks.origin` by the `session_id` it was asked for, None
        included.
    ambiguities : tuple of Ambiguity or None
        :func:`~escapewheel_reader.runs.ambiguities`.
    unit_windows : pyarrow.Table or None
        :func:`~escapewheel_reader.unit_windows` over every unit, which
        :func:`~escapewheel_reader.spike_times` filters per unit.
    """

    anchors: dict[int, tuple[NDArray[np.int64], NDArray[np.int64]]] | None = None
    clock_graph: ClockGraph | None = None
    bound: float | None = None
    reference_clock: int | None = None
    origins: dict[int | None, tuple[int, int, int]] = field(default_factory=dict)
    ambiguities: tuple[Ambiguity, ...] | None = None
    unit_windows: pa.Table | None = None

    @classmethod
    def of(cls, packet: object) -> Memo:
        """Return the packet's memo, or an empty one for a stand-in that keeps none.

        Such a stand-in is read again on every call.
        """
        kept = getattr(packet, "memo", None)
        return kept if isinstance(kept, cls) else cls()


class PacketLike(Protocol):
    """Resolution and reading of one packet's resources, as the free functions use them."""

    @property
    def memo(self) -> Memo:
        """What the free functions have read from this packet and keep."""

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

    def table(
        self,
        resource_id: str,
        *,
        columns: list[str] | None = None,
        on_clock: bool | int = False,
        seconds: bool = False,
        **where: Predicate,
    ) -> pa.Table:
        """Read a table resource into memory, optionally narrowed and put on one clock."""

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


@runtime_checkable
class PacketSetLike(Protocol):
    """What a transform or predicate asks of several packets: the packet and session each `session_key` names.

    A clock ID means something only within its packet, so each row is resolved in the packet its
    `session_key` names. The two methods are the reader's own, so only
    :class:`~escapewheel_reader.PacketSet` implements this.
    """

    @property
    def sessions(self) -> tuple[Session, ...]:
        """Every packet's sessions, each with its `session_key`."""
        ...

    def _located(self, session_key: int) -> tuple[PacketLike, Session]: ...

    def _keyed(self, resource_id: str) -> list[tuple[PacketLike, list[int]]]: ...


__all__ = ["Memo", "PacketLike", "PacketSetLike"]
