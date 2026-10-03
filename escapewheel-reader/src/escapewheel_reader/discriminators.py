"""The rows a discriminator's kind names (Part 02 §8.3, Part 05 §13.4).

- :func:`resolved` -- the rows of one kind joined to the resource it names.
- :func:`specialised` -- :func:`resolved` for every kind the rows name.
- :func:`kinds` -- each value the rows name, and how many name it.
- :func:`declared` -- every discriminator the packet's registries declare, extensions included.
- :func:`unresolved` -- what a packet names and does not hold, at its declared level.
- :func:`registries` -- every table the packet's registries declare.
- :class:`Discriminator`, :class:`Unresolved` -- what the functions return.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc

from .errors import NotDeclared
from .optional import held
from .protocols import PacketLike
from .registries import declared_tables

#: The field a discriminator declares beyond its role to take the paired-value shape.
SHAPES = {"discriminates": "paired value"}


@dataclass(frozen=True)
class Discriminator:
    """One declared discriminator, and how its value resolves."""

    resource: str
    column: str
    resolves: str
    discriminates: str | None = None
    discriminates_via: str | None = None

    @property
    def shape(self) -> str:
        """Which of the two resolutions applies: paired value, or shared key without one."""
        for field, name in SHAPES.items():
            if getattr(self, field) is not None:
                return name
        return "shared key"

    @property
    def specialised(self) -> str:
        """The resource whose rows the kind specialises.

        Usually the table carrying the column. Where `discriminates_via` is declared the
        discriminator sits one reference away, so the specialised rows are the referencing
        table's.
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
        """What the discriminator's `resolves` makes of it.

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


def registries(packet: PacketLike) -> dict[str, Any]:
    """Every table the packet's own registries declare, core and extensions together.

    Built over every registry a packet carries, as anything reading a discriminator must be: an
    extension kind matching no branch and passing in silence is the one case the mechanism exists
    to cover.
    """
    tables = declared_tables(packet.registry)
    for document in packet.extensions().values():
        tables.update(declared_tables(document))
    return tables


def declared(packet: PacketLike) -> list[Discriminator]:
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
                )
            )
    return found


def _one(packet: PacketLike, resource_id: str, column: str | None) -> Discriminator:
    """Find the discriminator on a resource, or the named one where a table declares several."""
    on = [d for d in declared(packet) if d.resource == resource_id and (column is None or d.column == column)]
    if not on:
        named = f" named {column}" if column else ""
        raise NotDeclared(f"{resource_id} declares no discriminator{named}")
    if len(on) > 1:
        raise NotDeclared(
            f"{resource_id} declares several discriminators; name one of {', '.join(sorted(d.column for d in on))}"
        )
    return on[0]


def kinds(packet: PacketLike, resource_id: str, column: str | None = None) -> dict[str | None, int]:
    """Each value the rows name, and how many name it.

    `None` counts the rows declaring no kind, which are undeterminable rather than unresolvable
    and which a consumer reports apart from a value naming nothing.
    """
    found = _one(packet, resource_id, column)
    counts = pc.value_counts(packet.table(found.resource, columns=[found.column]).column(found.column))
    named: list[str | None] = counts.field("values").to_pylist()
    counted = [int(n) for n in counts.field("counts").to_numpy()]
    return dict(zip(named, counted, strict=True))


def unresolved(packet: PacketLike) -> list[Unresolved]:
    """Every kind a packet names and does not hold, and every row naming none.

    Reports rather than raises. An unresolvable value is a defect only where `resolves` is
    `required`; where it is `optional` the packet is saying it does not hold that resource, which
    is a fact about the packet and not a fault in it.
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


def _reference_back(packet: PacketLike, source: str, target: str) -> tuple[list[str], list[str]]:
    """Find the specialised table's one reference to the discriminator's, as (its columns, the key's).

    The table `discriminates_via` names declares exactly one.
    """
    for reference in registries(packet).get(source, {}).get("references", []):
        if reference.get("resource") == target:
            return list(reference["columns"]), list(reference["resource_columns"])
    raise NotDeclared(f"{source} declares no reference to {target}, which discriminates_via requires")


def _specialising_reference(packet: PacketLike, kind: str, found: Discriminator) -> tuple[list[str], list[str]]:
    """Find the named resource's specialising reference naming the discriminator, as (its columns, the key's).

    Shared-key resolution joins through that reference; a named resource declaring none is not
    a specialisation of the discriminator, whatever else it references.
    """
    named = f"{found.resource}.{found.column}"
    for reference in registries(packet).get(kind, {}).get("references", []):
        if reference.get("specialises") == named:
            return list(reference["columns"]), list(reference["resource_columns"])
    raise NotDeclared(f"{kind} declares no specialising reference naming {named}")


def _key(packet: PacketLike, resource: str) -> list[str]:
    """Read a resource's primary key, as the packet's own registry declares it."""
    return list(registries(packet).get(resource, {}).get("primary_key") or [])


def _paired_target(packet: PacketLike, kind: str, found: Discriminator) -> str:
    """Find the column a paired value joins to.

    An identifier value holds the named key's own value, so it joins the key. A string value joins
    the key where it is carried, and where it is assigned the `*_name` its owner carries, since a
    string cannot hold a number the packet mints (Part 02 §8.2).
    """
    key = _key(packet, kind)
    if len(key) != 1:
        raise NotDeclared(f"{kind} has a {len(key)}-column key, which a paired value cannot name")
    holder = registries(packet).get(found.specialised, {}).get("columns", [])
    value: dict[str, Any] = next((c for c in holder if c["name"] == found.discriminates), {})
    declared_columns = {c["name"]: c for c in registries(packet).get(kind, {}).get("columns", [])}
    if value.get("role") == "identifier" or declared_columns.get(key[0], {}).get("identity") != "assigned":
        return key[0]
    named = f"{key[0].removesuffix('_id')}_name"
    if named not in declared_columns:
        raise NotDeclared(f"{kind} keys on an assigned {key[0]} and carries no {named} to match a paired value against")
    return named


def resolved(packet: PacketLike, resource_id: str, kind: str, *, column: str | None = None) -> pa.Table:
    """Join the rows of one kind to the resource its discriminator names.

    Parameters
    ----------
    packet : PacketLike
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
        The specialised rows of that kind with the named resource's columns joined on. A paired
        value that is null names no row, so its row is not returned.

    Raises
    ------
    NotDeclared
        If the resource declares no such discriminator, or the packet does not hold the kind.
    """
    found = _one(packet, resource_id, column)
    if kind not in held(packet):
        raise NotDeclared(f"the packet does not hold {kind}, which {found.resource}.{found.column} names")
    named = packet.table(kind)

    rows = packet.table(found.specialised)
    if found.shape == "paired value":
        if found.discriminates_via is None:
            rows = rows.filter(pc.equal(rows.column(found.column), pa.scalar(kind)))
        else:
            # The kind is on the discriminator's row, one reference away from the value.
            ours, theirs = _reference_back(packet, found.specialised, found.resource)
            of_kind = packet.table(found.resource, columns=[*theirs, found.column])
            of_kind = of_kind.filter(pc.equal(of_kind.column(found.column), pa.scalar(kind))).select(theirs)
            rows = rows.join(of_kind, keys=ours, right_keys=theirs, join_type="inner")
        # Per kind, since the values of two kinds share one column and may coincide.
        assert found.discriminates is not None
        target = _paired_target(packet, kind, found)
        return rows.join(named, keys=[found.discriminates], right_keys=[target], join_type="inner")

    # Against the **discriminated** table, which `discriminates_via` moves away from the one
    # carrying the column: a detail table shares a key with the rows it specialises.
    theirs, ours = _specialising_reference(packet, kind, found)
    # The key need not hold the kind -- `core.intervals` keys on `interval_id` alone -- so the rows
    # are filtered to it, and a column both tables carry, such as `session_id`, is kept once.
    rows = rows.filter(pc.equal(rows.column(found.column), pa.scalar(kind)))
    named = named.select([c for c in named.column_names if c in theirs or c not in rows.column_names])
    return rows.join(named, keys=ours, right_keys=theirs, join_type="inner")


def specialised(packet: PacketLike, resource_id: str, *, column: str | None = None) -> dict[str, pa.Table]:
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


__all__ = ["Discriminator", "Unresolved", "declared", "kinds", "resolved", "specialised", "unresolved"]
