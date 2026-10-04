"""Columns that may be dictionary-encoded, handled without branching.

- :func:`values` -- a column's distinct values, from its dictionary where it has one.
- :func:`where` -- offsets where a column equals a value, comparing codes where it is a dictionary.
- :func:`constant` -- one repeated value as codes into a one-entry dictionary.
- :func:`decoded` -- a table with its dictionary columns decoded.
- :func:`join` -- an Arrow join on keys that may be dictionaries or differ in width.
- :func:`lookup` -- the parent value each row's key names, in the rows' order.
- :func:`key_filter` / :func:`within` -- rows whose keys together match a wanted row.
- :func:`one_of` / :func:`any_of` -- membership and disjunction as expressions a scan prunes by.

Arrow cannot sort a dictionary column, and `group_by` fails across row groups until
`Table.unify_dictionaries` reconciles them. Its joins take no dictionary key and no keys of
different widths, and the helpers below decode and cast so a caller need not.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import reduce
from typing import Any, Literal

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from numpy.typing import NDArray


def constant(value: Any, rows: int, type_: pa.DataType | None = None) -> pa.DictionaryArray[Any, Any]:
    """Return one repeated value as codes into a one-entry dictionary."""
    return pa.DictionaryArray.from_arrays(np.zeros(rows, dtype=np.int32), pa.array([value], type=type_))


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


def plain(column: Any) -> Any:
    """Decode a dictionary column, leaving any other as it is."""
    return column.cast(column.type.value_type) if pa.types.is_dictionary(column.type) else column


def decoded(table: pa.Table) -> pa.Table:
    """Decode every dictionary column of a table."""
    return table.cast(
        pa.schema(pa.field(f.name, f.type.value_type) if pa.types.is_dictionary(f.type) else f for f in table.schema)
    )


def join(
    left: pa.Table,
    right: pa.Table,
    keys: Sequence[str],
    join_type: Literal["inner", "left outer", "left semi", "left anti"] = "inner",
) -> pa.Table:
    """Join on `keys`, decoded and cast to the left's types. Row order is not kept."""
    left, right = decoded(left), decoded(right)
    for key in keys:
        right = right.set_column(
            right.column_names.index(key), key, right.column(key).cast(left.schema.field(key).type)
        )
    return left.join(right, keys=list(keys), join_type=join_type)


def lookup(keys: Sequence[Any], parent: pa.Table, parent_keys: Sequence[str], column: str) -> Any:
    """Return `column` of the parent row each position of `keys` names, null where none does.

    Raises
    ------
    ValueError
        Where the parent holds one key on several rows, which would give a row several answers.
    """
    parent = decoded(parent)
    if parent.group_by(list(parent_keys)).aggregate([]).num_rows != parent.num_rows:
        raise ValueError("the parent holds a key on more than one row")
    local = [plain(key).cast(parent.schema.field(name).type) for key, name in zip(keys, parent_keys, strict=True)]
    if len(local) == 1:
        return pc.take(
            parent.column(column), pc.index_in(local[0], value_set=parent.column(parent_keys[0]).combine_chunks())
        )
    # A left join keeps every row, and the row number restores the order the join does not.
    named = [f"k{i}" for i in range(len(local))]
    rows = pa.table({**dict(zip(named, local, strict=True)), "row": pa.array(np.arange(len(local[0])))})
    values = pa.table(
        {**{k: parent.column(n) for k, n in zip(named, parent_keys, strict=True)}, "value": parent.column(column)}
    )
    return rows.join(values, keys=named, join_type="left outer").sort_by("row").column("value")


def key_filter(wanted: pa.Table, keys: Sequence[str]) -> tuple[pc.Expression, bool]:
    """Return a scan filter keeping rows whose every key is among `wanted`'s, and whether it is exact.

    Per-key membership is what a Parquet scan can push down, and it admits a row matching each
    key on a different wanted row. It is exact where the wanted keys are every combination of
    their values, which one key, or one session, always is.
    """
    wanted = decoded(wanted.select(list(keys)))
    tests = [one_of(key, pc.unique(wanted.column(key).drop_null())) for key in keys]
    combinations = reduce(lambda n, key: n * len(pc.unique(wanted.column(key))), keys, 1)
    exact = combinations == wanted.group_by(list(keys)).aggregate([]).num_rows
    return reduce(lambda a, b: a & b, tests), exact


#: The most values one `is_in` test may hold and still be checked against row-group statistics;
#: past it PyArrow keeps every row group.
PRUNABLE_VALUES = 50


def one_of(column: str, values: Any) -> pc.Expression:
    """Test `column` for membership in `values`, as sorted runs short enough for row groups to prune by."""
    found = pc.unique(values if isinstance(values, (pa.Array, pa.ChunkedArray)) else pa.array(list(values)))
    if len(found) <= PRUNABLE_VALUES:
        return pc.field(column).isin(found)
    ordered = found.take(pc.sort_indices(found))
    runs = range(0, len(ordered), PRUNABLE_VALUES)
    return any_of([pc.field(column).isin(ordered[start : start + PRUNABLE_VALUES]) for start in runs])


def any_of(terms: Sequence[pc.Expression]) -> pc.Expression:
    """OR `terms` as a balanced tree, whose depth stays logarithmic in their number."""
    if len(terms) == 1:
        return terms[0]
    middle = len(terms) // 2
    return any_of(terms[:middle]) | any_of(terms[middle:])


def within(table: pa.Table, wanted: pa.Table, keys: Sequence[str]) -> pa.Table:
    """Keep the rows of `table` whose keys together match a row of `wanted`, in their order."""
    numbered = table.append_column("__row", pa.array(np.arange(table.num_rows)))
    kept = join(numbered, wanted.select(list(keys)), keys, "left semi").sort_by("__row")
    return kept.drop_columns("__row").select(table.column_names)


__all__: list[str] = []
