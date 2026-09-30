"""The order a table is stored in, which the physical-profile descriptor declares.

A table is stored in its primary key's order unless the descriptor's table interface names it in
`overriding_orders` (Part 03 §5.4). A writer emits the order and a validator establishes it (Part 03
§5.3), and both read it here, from the descriptor this package vendors.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import cache
from typing import Any

from .profile import physical_profile


@cache
def _overrides() -> Mapping[str, tuple[str, ...]]:
    profile = physical_profile()
    interface = profile["interfaces"][profile["kind_interfaces"]["table"]]
    return {resource: tuple(order) for resource, order in interface.get("overriding_orders", {}).items()}


def stored_order(resource: str, table: Mapping[str, Any]) -> list[str]:
    """Return the columns `resource` is stored by, in order.

    Empty where the table declares no primary key and no override, which is the one case with no
    order to establish (Part 02 §2 admits a `null` key with a stated reason).
    """
    if override := _overrides().get(resource):
        return list(override)
    return list(table.get("primary_key") or ())


def overridden(resource: str) -> Sequence[str] | None:
    """Part 03 §5.4's order for `resource`, or None where its key is its order."""
    override = _overrides().get(resource)
    return list(override) if override else None


def override_errors(order: Sequence[str], table: Mapping[str, Any] | None) -> list[str]:
    """Where an overriding order is inconsistent with the table a core registry declares.

    The conditions of Part 03 §5.4 that let an override settle its key by adjacency without a
    packet (Part 03 §5.3). `table` is None where the registry declares no such table.
    """
    if table is None:
        return ["the core registry declares no such table"]
    columns = {column["name"]: column for column in table.get("columns", ())}
    key = list(table.get("primary_key") or ())
    errors = [f"{name!r} is not a column of the table" for name in order if name not in columns]
    errors += [f"key column {name!r} is absent" for name in key if name not in order]
    if errors:
        return errors
    last = max(order.index(name) for name in key)
    for name in order[:last]:
        determined = columns[name].get("determined_by")
        if name not in key and not (determined and set(determined) <= set(key)):
            errors.append(f"{name!r} precedes a key column and is not determined by the key")
    if list(order) == key:
        errors.append("the order is the table's primary key's order")
    return errors


__all__ = ["overridden", "override_errors", "stored_order"]
