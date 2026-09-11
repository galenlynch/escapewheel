"""The order a table is stored in, which the registry no longer declares.

R93 §3.3 removed the per-table `sort` field: it stated a physical property in the logical
standard's machine form, and a reader could not tell a table with no override from one a later
build block forgot. Part 03 §5.4's table is the only statement an override has now, and two actors
read it -- a writer emits the order (Part 03 §5.4) and a validator establishes it (Part 03 §5.3) -- so
the machine copy lives here, in the package both of them depend on and neither of which depends
on the other.

Everything not named below is stored in its primary key's order (Part 03 §5.3).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

#: Part 03 §5.4. `analysis.spike_events` buckets by time and sorts by unit within each bucket, so a
#: time filter and a unit filter each prune (Part 03 §5.4, narrowed to five columns by R81 §2.4). It
#: satisfies Part 03 §5.3 because `clock_id` and `time_bucket_tick` are each declared `determined_by`
#: a subset of the key, so neither can separate two rows that share one.
OVERRIDES: Mapping[str, tuple[str, ...]] = {
    "analysis.spike_events": ("session_id", "clock_id", "time_bucket_tick", "unit_id", "t_tick"),
}


def stored_order(resource: str, table: Mapping[str, Any]) -> list[str]:
    """The columns `resource` is stored by, in order.

    Empty where the table declares no primary key and no override, which is the one case with no
    order to establish (Part 02 §2 admits a `null` key with a stated reason).
    """
    if override := OVERRIDES.get(resource):
        return list(override)
    return list(table.get("primary_key") or ())


def overridden(resource: str) -> Sequence[str] | None:
    """Part 03 §5.4's order for `resource`, or None where its key is its order."""
    override = OVERRIDES.get(resource)
    return list(override) if override else None


__all__ = ["OVERRIDES", "overridden", "stored_order"]
