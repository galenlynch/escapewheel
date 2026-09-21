"""Working with columns that may be dictionary-encoded.

Parquet stores a low-cardinality string column as codes into a dictionary held once per row
group, so a reader meets one wherever such a column is read without decoding -- which the
validator's ordering scan does deliberately, since `core.events`, `core.trial_tags` and
`core.session_experimenters` all sort on a string. These helpers take the dictionary where
there is one and the column itself where there is not, so a caller does not branch.

Two operations remain unimplemented for a dictionary column whatever is done to it: Arrow
cannot sort one, and `group_by` raises `Unifying differing dictionaries` across row groups
until `Table.unify_dictionaries` reconciles them. Both fail loudly. Comparison, `is_in`,
`unique` and filtering all work.

The helpers are small; the reason they are shared is that the reader, the writer and the
validator all meet the same edges, and a second implementation of any of them would differ
silently.
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
    columns that happened to have it and raise for the rest, which is the failure R53 §2.1
    produced by turning every identifier into an integer.
    """
    if pa.types.is_dictionary(column.type):
        code = column.dictionary.index(value).as_py()
        if code is None or code < 0:
            return np.empty(0, dtype=np.int64)
        matches = pc.equal(column.indices, pa.scalar(code, column.indices.type))
    else:
        matches = pc.equal(column, pa.scalar(value, column.type))
    return np.flatnonzero(pc.fill_null(matches, False).to_numpy(zero_copy_only=False))


__all__ = ["constant", "values", "where"]
