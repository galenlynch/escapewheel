"""A table's rows gathered into one row per key, from the order they are stored in.

- :func:`ragged` -- one row per key, its other columns as lists of its values.

A table is stored so that rows sharing a key are neighbours (Part 03 §5.3), so each key's rows are
already one run and gathering them needs no sort and no copy of the values: a list column is the
values with offsets laid over them. A reader may not depend on that order for correctness, so the
runs are checked to ascend and a departure is refused.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any, cast, overload

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as pads

from .dictionaries import plain
from .errors import NotDeclared, Unordered
from .ordering import stored_order
from .protocols import PacketLike

#: What :func:`ragged` takes: one in memory, or a stream it gathers batch by batch.
Stream = pa.RecordBatchReader | pads.Scanner | pads.Dataset


@overload
def ragged(packet: PacketLike, data: pa.Table, resource_id: str) -> pa.Table: ...
@overload
def ragged(packet: PacketLike, data: pa.RecordBatch, resource_id: str) -> pa.RecordBatch: ...
@overload
def ragged(packet: PacketLike, data: Stream, resource_id: str) -> pa.RecordBatchReader: ...
def ragged(
    packet: PacketLike, data: pa.Table | pa.RecordBatch | Stream, resource_id: str
) -> pa.Table | pa.RecordBatch | pa.RecordBatchReader:
    """Return one row per key of `resource_id`'s rows, each other column a list of that key's values.

    The key is every column of the resource's stored order but its last that `data` holds; for
    `core.spike_events` that is `(session_id, unit_id)`, so each unit becomes one row with its
    `t_tick` a list. Leaving a key column out gathers by those that remain, which holds only where
    their rows are still neighbours: `analysis.spike_events` read without `time_bucket_tick` is
    refused rather than gathered by unit. A key's values keep the order they were stored in.

    Parameters
    ----------
    packet : PacketLike
        The packet whose registry declares the resource's order.
    data : pyarrow.Table, RecordBatch, RecordBatchReader, or pyarrow.dataset Scanner or Dataset
        Rows of `resource_id` in the order they were read, filtered or not. A stream is gathered
        batch by batch, a run cut by a batch's end joined to its remainder before it is yielded.
    resource_id : str
        The resource the rows are of.

    Returns
    -------
    pyarrow.Table, RecordBatch or RecordBatchReader
        The key columns, then every other column as a `large_list` of its type, in the form `data`
        came in. A table's lists share its buffers; only a run a chunk's end cuts is copied.

    Raises
    ------
    NotDeclared
        If the resource declares no primary key and no stored order, so no key exists to gather by.
    Unordered
        If a key's rows are not together, so gathering them would need a sort. A stream raises
        when it reaches the run out of place, having yielded the runs before it.
    """
    declaration = packet.resource(resource_id).declaration or {}
    order = stored_order(resource_id, declaration.get("table", {}))
    if not order:
        raise NotDeclared(f"{resource_id} declares no primary key and no stored order to gather its rows by")
    schema = data.projected_schema if isinstance(data, pads.Scanner) else data.schema
    keys = [name for name in order[:-1] if name in schema.names]
    listed = [name for name in schema.names if name not in keys]
    out_schema = pa.schema(
        [schema.field(name) for name in keys]
        + [pa.field(name, pa.large_list(schema.field(name).type)) for name in listed]
    )
    if isinstance(data, pa.Table):
        parts = list(_gathered(data.to_batches(), keys, listed, out_schema))
        return pa.Table.from_batches(parts, schema=out_schema)
    if isinstance(data, pa.RecordBatch):
        gathered = pa.Table.from_batches(list(_gathered([data], keys, listed, out_schema)), schema=out_schema)
        return (
            gathered.combine_chunks().to_batches()[0]
            if gathered.num_rows
            else pa.RecordBatch.from_pylist([], schema=out_schema)
        )
    if isinstance(data, pads.Dataset):
        data = data.scanner()
    reader = data.to_reader() if isinstance(data, pads.Scanner) else data
    if not isinstance(reader, pa.RecordBatchReader):
        raise TypeError(
            f"expected a pyarrow Table, RecordBatch, RecordBatchReader, Scanner or Dataset, not {type(data)}"
        )
    return pa.RecordBatchReader.from_batches(out_schema, _gathered(reader, keys, listed, out_schema))


def _gathered(batches: Any, keys: Sequence[str], listed: Sequence[str], schema: pa.Schema) -> Iterator[pa.RecordBatch]:
    """Yield each batch's complete runs, holding back its last until the next batch shows where it ends."""
    held: _Run | None = None
    previous: list[Any] | None = None
    for batch in batches:
        if not batch.num_rows:
            continue
        offsets = _run_offsets(batch, keys)
        firsts = pa.array(offsets[:-1])
        run_keys = [batch.column(name).take(firsts) for name in keys]
        first = 0
        if held is not None and _same(held.keys, [key.slice(0, 1) for key in run_keys]):
            held.extend(batch, listed, offsets[0], offsets[1])
            first = 1
            if len(offsets) == 2:
                continue
        complete: list[pa.RecordBatch] = []
        if held is not None:
            complete.append(held.batch(listed, schema))
        last = len(offsets) - 2
        if last > first:
            middle = offsets[first : last + 1]
            lists = [
                pa.LargeListArray.from_arrays(
                    pa.array(middle - middle[0]), batch.column(name).slice(middle[0], middle[-1] - middle[0])
                )
                for name in listed
            ]
            complete.append(
                pa.RecordBatch.from_arrays([key.slice(first, last - first) for key in run_keys] + lists, schema=schema)
            )
        held = _Run([key.slice(last, 1) for key in run_keys])
        held.extend(batch, listed, offsets[last], offsets[last + 1])
        for part in complete:
            previous = _check_ascending(previous, part, keys)
            yield part
    if held is not None:
        part = held.batch(listed, schema)
        _check_ascending(previous, part, keys)
        yield part


class _Run:
    """One key's run while a batch's end may still cut it, its values kept as the slices that hold them."""

    def __init__(self, keys: list[Any]) -> None:
        self.keys = keys
        self.pieces: list[list[Any]] = []

    def extend(self, batch: pa.RecordBatch, listed: Sequence[str], start: int, stop: int) -> None:
        self.pieces.append([batch.column(name).slice(start, stop - start) for name in listed])

    def batch(self, listed: Sequence[str], schema: pa.Schema) -> pa.RecordBatch:
        lists = []
        for column in range(len(listed)):
            pieces = [piece[column] for piece in self.pieces]
            values = pieces[0] if len(pieces) == 1 else pa.concat_arrays(pieces)
            lists.append(pa.LargeListArray.from_arrays(pa.array([0, len(values)], pa.int64()), values))
        return pa.RecordBatch.from_arrays([*self.keys, *lists], schema=schema)


def _run_offsets(batch: pa.RecordBatch, keys: Sequence[str]) -> Any:
    """Offsets of each run of equal keys in `batch`, ending with its length; a null equals a null."""
    rows = batch.num_rows
    changed = np.zeros(rows - 1, dtype=bool)
    for name in keys:
        column = batch.column(name)
        # One batch holds one dictionary, so codes compare as the values do.
        column = cast("pa.DictionaryArray[Any, Any]", column).indices if pa.types.is_dictionary(column.type) else column
        if not column.null_count and (pa.types.is_integer(column.type) or pa.types.is_floating(column.type)):
            flat = column.to_numpy()
            changed |= flat[1:] != flat[:-1]
            continue
        before, after = column.slice(0, rows - 1), column.slice(1)
        differs = pc.not_equal(before, after)
        if differs.null_count:
            differs = pc.fill_null(differs, pc.xor(pc.is_null(before), pc.is_null(after)))
        changed |= differs.to_numpy(zero_copy_only=False)
    return np.concatenate(([0], np.flatnonzero(changed) + 1, [rows])).astype(np.int64)


def _same(left: Sequence[Any], right: Sequence[Any]) -> bool:
    """Whether two one-row key lists hold the same values, a null equal to a null."""
    return all(plain(a).to_pylist() == plain(b).to_pylist() for a, b in zip(left, right, strict=True))


def _check_ascending(previous: list[Any] | None, part: pa.RecordBatch, keys: Sequence[str]) -> list[Any]:
    """Refuse unless each run's key follows the one before it, and return `part`'s last key.

    Ascending is what the stored order makes of every run of a conforming table, and it is checked
    on runs rather than rows, so a key that reappears after another is found wherever it is.
    """
    columns = [plain(part.column(name)) for name in keys]
    if previous is not None:
        columns = [pa.concat_arrays([before, column]) for before, column in zip(previous, columns, strict=True)]
    rows = len(columns[0]) if columns else 0
    if rows > 1:
        settled = np.zeros(rows - 1, dtype=bool)
        descends = np.zeros(rows - 1, dtype=bool)
        for column in columns:
            before, after = column.slice(0, rows - 1), column.slice(1)
            less = pc.fill_null(pc.less(before, after), False).to_numpy(zero_copy_only=False)
            greater = pc.fill_null(pc.greater(before, after), False).to_numpy(zero_copy_only=False)
            descends |= ~settled & greater
            settled |= less | greater
        # Two neighbouring runs can be equal only where a key is null, which no key column holds.
        if descends.any() or not settled.all():
            at = int(np.flatnonzero(descends | ~settled)[0]) + 1
            key = {name: column[at].as_py() for name, column in zip(keys, columns, strict=True)}
            raise Unordered(f"the run of {key} follows a run it should precede, so its key's rows are not together")
    return [column.slice(rows - 1) for column in columns]


__all__ = ["ragged"]
