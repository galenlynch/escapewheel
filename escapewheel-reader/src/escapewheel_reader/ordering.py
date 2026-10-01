"""The order a table is stored in, as the physical-profile descriptor declares it (Part 03 §5.4).

- :func:`stored_order` -- the columns a resource is stored by.
- :func:`overridden` -- the descriptor's overriding order for a resource, or None.

A table is stored in its primary key's order unless the descriptor overrides it. The writer emits
that order and the validator checks it, both through this module.
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


__all__ = ["stored_order"]
