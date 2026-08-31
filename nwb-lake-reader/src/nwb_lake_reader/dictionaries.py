"""Working with dictionary-encoded columns.

A packet's identity columns -- `unit_id`, `clock_id`, `session_id` -- are dictionary-encoded
in Parquet and stay that way in Arrow wherever it is affordable, because decoding one string
per spike is what makes a 287 M-row table expensive. Everything here exists because that
choice has consequences at every boundary: a dictionary column will not compare against a
string scalar, `pc.equal` decodes before it compares, and concatenating string chunks past
2 GB overflows the offset type. The helpers are small; the reason they are shared is that
the reader, the writer and the validator all meet the same edges, and a second
implementation of any of them would differ silently.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from numpy.typing import NDArray


def as_dictionary(table: pa.Table, columns: Iterable[str]) -> pa.Table:
    """Re-encode named string columns as dictionaries, leaving the rest alone.

    Used to give one return type to two read strategies. A whole-file read gets its
    dictionary from Parquet directly, which is the cheap direction; a filtered read is faster
    decoded and then re-encoded here, because the rows a filter leaves are few. Measured on
    572,551 rows: 0.041 s decoded, 0.019 s to re-encode, against 1.318 s asking the scanner
    for dictionaries -- and 132.8 MB becomes 18.5 MB.
    """
    wanted = set(columns)
    if not wanted:
        return table
    arrays, fields = [], []
    for name in table.schema.names:
        column = table.column(name)
        if name in wanted and pa.types.is_string(column.type):
            column = pc.dictionary_encode(column)
        arrays.append(column)
        fields.append(pa.field(name, column.type))
    return pa.table(arrays, schema=pa.schema(fields))


def constant(value: str, rows: int) -> pa.DictionaryArray[Any, Any]:
    """Return one repeated string as codes into a one-entry dictionary."""
    return pa.DictionaryArray.from_arrays(pa.array([0] * rows, type=pa.int32()), pa.array([value]))


def values(column: Any) -> list[str]:
    """Distinct values of a string column, read from the dictionary where there is one.

    A dictionary already lists them, so this is a read of a handful of entries rather than a
    scan. It may name a value no row in this batch uses, which is why the caller skips an empty
    selection rather than trusting the list to be tight.
    """
    listed = column.dictionary if pa.types.is_dictionary(column.type) else pc.unique(column)
    return [v for v in listed.to_pylist() if v is not None]


def where(column: Any, value: str) -> NDArray[np.int64]:
    """Offsets where a string column equals `value`, comparing codes where it is a dictionary."""
    if pa.types.is_dictionary(column.type):
        code = column.dictionary.index(value).as_py()
        if code is None or code < 0:
            return np.empty(0, dtype=np.int64)
        matches = pc.equal(column.indices, pa.scalar(code, column.indices.type))
    else:
        matches = pc.equal(column, pa.scalar(value, pa.string()))
    return np.flatnonzero(pc.fill_null(matches, False).to_numpy(zero_copy_only=False))


__all__ = ["as_dictionary", "constant", "values", "where"]
