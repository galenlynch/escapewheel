"""Row constraints as Arrow expressions, usable on any dataset or scanner.

- :func:`where` -- column constraints as one expression.
- :data:`Predicate` -- what one constraint may be.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pyarrow.compute as pc
import pyarrow.dataset as pads

#: One column's constraint: a scalar is equality, a two-item tuple a closed range, a list or set
#: membership, and None no constraint.
Predicate = str | int | float | bool | tuple[Any, Any] | list[Any] | set[Any] | frozenset[Any] | None


def expression(constraints: Mapping[str, Predicate]) -> pads.Expression | None:
    """Build the expression for `constraints`, or None where they constrain nothing.

    An unknown column raises when the expression is applied, rather than silently matching nothing.
    Membership exists because several streams may carry one kind of event: resolving a type gives
    a set of keys, and pushing them down lets row-group statistics prune rather than reading and
    filtering.
    """
    found: pads.Expression | None = None
    for column, value in constraints.items():
        if value is None:
            continue
        field = pads.field(column)
        if isinstance(value, tuple):
            low, high = value
            term = (field >= low) & (field <= high)
        elif isinstance(value, (list, set, frozenset)):
            term = field.isin(list(value))
        else:
            term = field == value
        found = term if found is None else found & term
    return found


def where(**constraints: Predicate) -> pads.Expression:
    """Return column constraints as one expression, for a dataset's or scanner's `filter`.

    The same constraints :meth:`Packet.table` takes as keywords, on the values as stored.

    Examples
    --------
    >>> packet.scan("core.events").to_table(filter=where(stream_id=[1, 3], t_tick=(0, 30_000)))  # doctest: +SKIP
    """
    found = expression(constraints)
    return pc.scalar(True) if found is None else found


def both(first: pads.Expression | None, second: pads.Expression | None) -> pads.Expression | None:
    """AND two optional expressions."""
    if first is None or second is None:
        return second if first is None else first
    return first & second


__all__ = ["Predicate", "where"]
