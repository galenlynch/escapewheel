"""Assign each name a packet uses its integer before any table is built (Part 05 §4.3).

- :func:`preassign` -- number every assigned identifier the added records name.
- :func:`paired_kinds` -- the numbering each identifier paired value on a table takes, by its row's kind.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from escapewheel_reader.registries import declared_tables
from escapewheel_reader.resource_ids import CORE_INTERVALS

from .keys import Keys
from .registries import Declarations


def preassign(tables: Mapping[str, Sequence[Mapping[str, Any]]], declarations: Declarations, keys: Keys) -> None:
    """Assign a number to every name this packet uses, before any table is built (Part 05 §4.3).

    Numbering as each table is staged would let the order tables happen to be written in
    decide the numbers: `core.sessions` names a `reference_clock_id` and is staged before
    `core.clocks`, so the clocks would be numbered by the session's mention of one of them.
    Two builds of the same sources must produce the same packet, which is what lets a rebuild
    be compared to what it replaced -- and that has to hold across tables, not only within one.
    """
    pending: dict[str, set[str]] = {}
    for resource_id, rows in sorted(tables.items()):
        spec = declarations.spec(resource_id)
        if spec is None:
            continue
        target = {
            column: referenced
            for ref in spec.get("references", [])
            for column, referenced in zip(ref["columns"], ref["resource_columns"], strict=True)
        }
        paired = paired_kinds(tables, declarations, resource_id)
        for column in spec["columns"]:
            name = column["name"]
            if column.get("role") != "identifier" or column.get("identity") != "assigned":
                continue
            for r in rows:
                if r.get(name) is not None:
                    kind = (paired[name](r) if name in paired else None) or target.get(name, name)
                    pending.setdefault(kind, set()).add(str(r[name]))
    for kind in sorted(pending):
        if kind == "interval_id":
            continue
        for value in sorted(pending[kind]):
            keys.of(kind, value)
    # Part 02 §12.9 numbers intervals by session, kind, clock and bounds, which only their rows
    # hold, so the rows order the names; a name no interval row carries is an orphan and follows.
    for row in sorted(tables.get(CORE_INTERVALS, []), key=lambda row: _interval_order(keys, row)):
        keys.of("interval_id", str(row["interval_id"]))
    for value in sorted(pending.get("interval_id", ())):
        keys.of("interval_id", value)


def _interval_order(keys: Keys, row: Mapping[str, Any]) -> tuple[int, str, int, int, int, str]:
    """Return where one `core.intervals` row falls in Part 02 §12.9's numbering."""
    return (
        keys.of("session_id", str(row["session_id"])),
        str(row["interval_kind"]),
        keys.of("clock_id", str(row["clock_id"])),
        int(row["start_tick"]),
        int(row["stop_tick"]),
        str(row["interval_id"]),
    )


def paired_kinds(
    tables: Mapping[str, Sequence[Mapping[str, Any]]], declarations: Declarations, resource_id: str
) -> dict[str, Callable[[Mapping[str, Any]], str | None]]:
    """Map each identifier paired value on a table to the numbering its row's kind names.

    Part 02 §8.3 lets an identifier hold the key of whichever resource its row's discriminator
    names, so its map is chosen per row: the named resource's one key column, which is the map
    that resource numbers its own key in. The kind is read off the records, which still hold
    names, so a value on a specialised table reaches its discriminator row by the names its
    reference carries.
    """
    found: dict[str, Callable[[Mapping[str, Any]], str | None]] = {}
    documents = declarations.documents
    for owner, table in ((n, t) for doc in documents for n, t in declared_tables(doc, strict=True).items()):
        for column in table["columns"]:
            if column.get("role") != "discriminator" or column.get("discriminates") is None:
                continue
            via = column.get("discriminates_via")
            holder = owner if via is None else str(via).rsplit(".", 1)[0]
            if holder != resource_id:
                continue
            found[column["discriminates"]] = _kind_reader(tables, declarations, owner, column["name"], resource_id)
    return found


def _kind_reader(
    tables: Mapping[str, Sequence[Mapping[str, Any]]],
    declarations: Declarations,
    owner: str,
    discriminator: str,
    holder: str,
) -> Callable[[Mapping[str, Any]], str | None]:
    """Return a function from a `holder` row to the key column of the resource its kind names."""

    def key_of(resource: Any) -> str | None:
        spec = declarations.spec(str(resource)) if resource is not None else None
        key = list((spec or {}).get("primary_key") or [])
        return key[0] if len(key) == 1 else None

    if owner == holder:
        return lambda row: key_of(row.get(discriminator))
    spec = declarations.spec(holder) or {}
    reference = next((r for r in spec.get("references", []) if r["resource"] == owner), None)
    if reference is None:
        return lambda row: None
    ours, theirs = list(reference["columns"]), list(reference["resource_columns"])
    kinds = {tuple(str(r.get(c)) for c in theirs): r.get(discriminator) for r in tables.get(owner, [])}
    return lambda row: key_of(kinds.get(tuple(str(row.get(c)) for c in ours)))


__all__ = ["paired_kinds", "preassign"]
