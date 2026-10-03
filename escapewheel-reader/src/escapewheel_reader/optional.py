"""Reading a table the packet need not hold.

- :func:`held` -- the resource IDs the packet declares.
- :func:`read_optional` -- the named columns of an optional table, absence reading as no rows or nulls.
"""

from __future__ import annotations

from collections.abc import Collection

import pyarrow as pa

from .errors import PacketError
from .protocols import PacketLike


def held(packet: PacketLike) -> frozenset[str]:
    """Return the resource IDs the packet declares."""
    return frozenset(r.resource_id for r in packet.resources())


def read_optional(
    packet: PacketLike, resource_id: str, columns: list[str], *, required: Collection[str] = ()
) -> pa.Table:
    """Read named columns of a small table, an absent table reading as no rows and an absent column as nulls.

    Most of the registry is optional, so absence is ordinary and a caller need not branch on it.
    A column the table lacks reads as type `null`, since nothing says what type it would have held.
    The whole table is read, which suits the run logs and catalogs this is for.

    Raises
    ------
    PacketError
        Where a held table lacks a column in `required`: reading that as nulls would turn a
        malformed table into a silently empty answer.
    """
    if resource_id not in held(packet):
        return pa.table({c: pa.array([], pa.null()) for c in columns})
    table = packet.table(resource_id)
    if absent := [c for c in columns if c in required and c not in table.column_names]:
        raise PacketError(f"{resource_id} carries no {', '.join(absent)}, which every row must")
    return pa.table({c: table.column(c) if c in table.column_names else pa.nulls(table.num_rows) for c in columns})


__all__ = ["held", "read_optional"]
