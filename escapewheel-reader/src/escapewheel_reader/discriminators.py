"""Resolve a discriminator: read the kind, take that resource's key, join.

Part 05 §13.4 asks a reader to offer this, and gives the reason: a discriminator nothing reads is a
free-form name with extra steps, which is what became of the mechanism it replaces. Without an
offer here every consumer of `core.intervals.interval_kind` writes the join again, and the join is
not obvious -- it takes three shapes, and reading one as another is what Part 02 §8.3's exclusion
exists to stop.

`declared` reports what a packet's own registries declare, core and extensions together, because a
kind naming an extension table is the case the mechanism exists for. `kinds` says which values a
table's rows actually name. `resolved` performs the join for one of them, and `unresolved` reports
what a packet names and does not hold, at the level Part 02 §8.3 assigns: a defect where `resolves`
is `required`, a fact where it is `optional`, and separately from a row that declares no kind at
all, since recording the missing half and correcting what a value names are different repairs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pyarrow as pa

#: The fields a discriminator declares beyond its role, each naming one of the three shapes.
SHAPES = {"discriminates": "paired value", "positions_in": "by position"}


@dataclass(frozen=True)
class Discriminator:
    """One declared discriminator, and how its value resolves."""

    resource: str
    column: str
    resolves: str
    discriminates: str | None = None
    discriminates_via: str | None = None
    positions_in: str | None = None

    @property
    def shape(self) -> str:
        """Which of Part 02 §8.3's three resolutions applies.

        A discriminator with neither `discriminates` nor `positions_in` is shared-key, which is
        why Part 02 §8.3 requires `positions_in` be declared: without it a by-position
        discriminator and a shared-key one are indistinguishable.
        """
        for field, name in SHAPES.items():
            if getattr(self, field) is not None:
                return name
        return "shared key"

    @property
    def specialised(self) -> str:
        """The resource whose rows the kind specialises.

        Usually the table carrying the column. Where `discriminates_via` is declared the
        discriminator sits one reference away, so the specialised rows are the referencing
        table's (Part 02 §8.3).
        """
        if self.discriminates_via is None:
            return self.resource
        return self.discriminates_via.rsplit(".", 1)[0]


@dataclass(frozen=True)
class Unresolved:
    """A kind a packet names and does not hold, or a row that names none."""

    discriminator: Discriminator
    kind: str | None
    rows: int

    @property
    def level(self) -> str:
        """What Part 02 §8.3 makes of it.

        A row declaring no kind is **undeterminable** whatever `resolves` says: the packet has
        not named a resource, so there is nothing to find missing.
        """
        if self.kind is None:
            return "undeterminable"
        return "defect" if self.discriminator.resolves == "required" else "fact"

    def __str__(self) -> str:
        """One line naming the column, the value and what is wrong with it."""
        where = f"{self.discriminator.resource}.{self.discriminator.column}"
        if self.kind is None:
            return f"{where}: {self.rows} row(s) declare no kind — undeterminable"
        return f"{where}: {self.rows} row(s) name {self.kind}, which the packet does not hold ({self.level})"


def _tables(document: Mapping[str, Any] | None) -> dict[str, Any]:
    """Take the tables a registry document declares, or nothing where there is no document."""
    return {
        str(name): declaration["table"]
        for name, declaration in (document or {}).get("resources", {}).items()
        if declaration.get("kind") == "table" and "table" in declaration
    }


def registries(packet: Any) -> dict[str, Any]:
    """Every table the packet's own registries declare, core and extensions together.

    Built over every registry a packet carries, which Part 02 §8.3 requires of anything reading a
    discriminator: an extension kind matching no branch and passing in silence is the one case the
    mechanism exists to cover.
    """
    tables = _tables(packet.registry)
    for document in packet.extensions().values():
        tables.update(_tables(document))
    return tables


def declared(packet: Any) -> list[Discriminator]:
    """Every discriminator the packet's registries declare."""
    found = []
    for resource, table in registries(packet).items():
        for column in table.get("columns", []):
            if column.get("role") != "discriminator":
                continue
            found.append(
                Discriminator(
                    resource=resource,
                    column=column["name"],
                    resolves=column.get("resolves", "required"),
                    discriminates=column.get("discriminates"),
                    discriminates_via=column.get("discriminates_via"),
                    positions_in=column.get("positions_in"),
                )
            )
    return found


def _one(packet: Any, resource_id: str, column: str | None) -> Discriminator:
    """Find the discriminator on a resource, or the named one where a table declares several."""
    on = [d for d in declared(packet) if d.resource == resource_id and (column is None or d.column == column)]
    if not on:
        named = f" named {column}" if column else ""
        raise LookupError(f"{resource_id} declares no discriminator{named}")
    if len(on) > 1:
        raise LookupError(
            f"{resource_id} declares several discriminators; name one of {', '.join(sorted(d.column for d in on))}"
        )
    return on[0]


def kinds(packet: Any, resource_id: str, column: str | None = None) -> dict[str | None, int]:
    """Each value the rows name, and how many name it.

    `None` counts the rows declaring no kind, which Part 02 §8.3 makes undeterminable rather than
    unresolvable and which a consumer reports apart from a value naming nothing.
    """
    found = _one(packet, resource_id, column)
    values = packet.table(found.resource, columns=[found.column]).column(found.column).to_pylist()
    counted: dict[str | None, int] = {}
    for value in values:
        counted[value] = counted.get(value, 0) + 1
    return counted


def unresolved(packet: Any) -> list[Unresolved]:
    """Every kind a packet names and does not hold, and every row naming none.

    Reports rather than raises. Part 02 §8.3 makes an unresolvable value a defect only where
    `resolves` is `required`; where it is `optional` the packet is saying it does not hold that
    resource, which is a fact about the packet and not a fault in it.
    """
    held = {r.resource_id for r in packet.resources()}
    out = []
    # A packet need not carry every table its registries declare, and a registry it does not
    # carry declares nothing to resolve.
    for found in (d for d in declared(packet) if d.resource in held):
        counted = kinds(packet, found.resource, found.column)
        for kind, rows in sorted(counted.items(), key=lambda item: (item[0] is not None, item[0])):
            if kind is None or kind not in held:
                out.append(Unresolved(found, kind, rows))
    return out


def _reference_back(packet: Any, kind: str, target: str) -> tuple[list[str], list[str]]:
    """Find the named resource's reference to the discriminated table, as (its columns, the key's).

    Part 02 §8.3 requires a shared-key target to declare one covering the discriminated table's
    whole key, because a reference on part of it resolves to several rows while the generated
    anti-join passes.
    """
    for reference in registries(packet).get(kind, {}).get("references", []):
        if reference.get("resource") == target:
            return list(reference["columns"]), list(reference["resource_columns"])
    raise LookupError(
        f"{kind} declares no reference back to {target}, which a shared-key "
        f"discriminator requires of what it names (Part 02 §8.3)"
    )


def _key(packet: Any, resource: str) -> list[str]:
    """Read a resource's primary key, as the packet's own registry declares it."""
    return list(registries(packet).get(resource, {}).get("primary_key") or [])


def _paired_target(packet: Any, kind: str) -> str:
    """Find the column a paired value joins to: the key where it is carried, its name where assigned.

    Part 02 §8.3 makes the value a `string`, and an assigned identifier is an `int32` a packet
    mints, so the value can only be the `*_name` its owner carries (Part 02 §8.2).
    """
    key = _key(packet, kind)
    if len(key) != 1:
        raise LookupError(f"{kind} has a {len(key)}-column key, which a paired value cannot name")
    declared_columns = {c["name"]: c for c in registries(packet).get(kind, {}).get("columns", [])}
    if declared_columns.get(key[0], {}).get("identity") != "assigned":
        return key[0]
    named = f"{key[0].removesuffix('_id')}_name"
    if named not in declared_columns:
        raise LookupError(
            f"{kind} keys on an assigned {key[0]} and carries no {named} to match a paired value against (Part 02 §8.3)"
        )
    return named


def resolved(packet: Any, resource_id: str, kind: str, *, column: str | None = None) -> pa.Table:
    """Join the rows of one kind to the resource its discriminator names.

    Parameters
    ----------
    packet : Packet
        An open packet.
    resource_id : str
        The table carrying the discriminator.
    kind : str
        One value of it, as `kinds` reports them.
    column : str, optional
        Which discriminator, where the table declares more than one.

    Returns
    -------
    pyarrow.Table
        The specialised rows with the named resource's columns joined on. For a by-position
        discriminator the named resource's rows are returned as they are: Part 02 §8.3 makes that
        shape neither a key join nor a value-to-key join, and forbids reading the joinability
        rules as applying to it.

    Raises
    ------
    LookupError
        If the resource declares no such discriminator, or the packet does not hold the kind.
    """
    found = _one(packet, resource_id, column)
    if kind not in {r.resource_id for r in packet.resources()}:
        raise LookupError(f"the packet does not hold {kind}, which {found.resource}.{found.column} names")
    named = packet.table(kind)

    if found.shape == "by position":
        return named

    rows = packet.table(found.specialised)
    if found.shape == "paired value":
        # The value is an identifier in the named resource's key space, and that key is one
        # column because a paired value holds one identifier (Part 02 §8.3).
        return rows.join(
            named, keys=[found.discriminates], right_keys=[_paired_target(packet, kind)], join_type="inner"
        )

    # Against the **discriminated** table, which `discriminates_via` moves away from the one
    # carrying the column: a detail table shares a key with the rows it specialises.
    theirs, ours = _reference_back(packet, kind, found.specialised)
    # The discriminator column is in the key for a shared-key join, so the join itself keeps
    # rows of other kinds out and no filter is needed.
    return rows.join(named, keys=ours, right_keys=theirs, join_type="inner")


def specialised(packet: Any, resource_id: str, *, column: str | None = None) -> dict[str, pa.Table]:
    """Every kind the rows name, resolved, keyed by the kind.

    A table whose rows name two kinds has no single resolution: the two carry different columns,
    so concatenating them is what a caller must not do and this does not offer.
    """
    found = _one(packet, resource_id, column)
    held = {r.resource_id for r in packet.resources()}
    return {
        kind: resolved(packet, resource_id, kind, column=found.column)
        for kind in kinds(packet, resource_id, found.column)
        if kind is not None and kind in held
    }


__all__ = [
    "Discriminator",
    "Unresolved",
    "declared",
    "kinds",
    "registries",
    "resolved",
    "specialised",
    "unresolved",
]
