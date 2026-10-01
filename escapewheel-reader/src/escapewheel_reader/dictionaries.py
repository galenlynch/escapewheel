"""Columns that may be dictionary-encoded, handled without branching.

- :func:`values` -- a column's distinct values, from its dictionary where it has one.
- :func:`where` -- offsets where a column equals a value, comparing codes where it is a dictionary.
- :func:`constant` -- one repeated value as codes into a one-entry dictionary.

Arrow cannot sort a dictionary column, and `group_by` fails across row groups until
`Table.unify_dictionaries` reconciles them.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from numpy.typing import NDArray


def constant(value: Any, rows: int, type_: pa.DataType | None = None) -> pa.DictionaryArray[Any, Any]:
    """Return one repeated value as codes into a one-entry dictionary."""
    return pa.DictionaryArray.from_arrays(pa.array([0] * rows, type=pa.int32()), pa.array([value], type=type_))


def values(column: Any) -> list[Any]:
    """Distinct values of a column, read from the dictionary where there is one.

    A dictionary already lists them, so this is a read of a handful of entries rather than a
    scan. It may name a value no row in this batch uses, which is why the caller skips an empty
    selection rather than trusting the list to be tight.
    """
    listed = column.dictionary if pa.types.is_dictionary(column.type) else pc.unique(column)
    return [v for v in listed.to_pylist() if v is not None]


def where(column: Any, value: Any) -> NDArray[np.int64]:
    """Offsets where a column equals `value`, comparing codes where it is a dictionary.

    The scalar takes the column's own type. Pinning it to one makes the helper work for the
    columns that happened to have it and raise for the rest.
    """
    if pa.types.is_dictionary(column.type):
        code = column.dictionary.index(value).as_py()
        if code is None or code < 0:
            return np.empty(0, dtype=np.int64)
        matches = pc.equal(column.indices, pa.scalar(code, column.indices.type))
    else:
        matches = pc.equal(column, pa.scalar(value, column.type))
    return np.flatnonzero(pc.fill_null(matches, False).to_numpy(zero_copy_only=False))


__all__: list[str] = []
