"""Write one table's rows to Parquet as the portable profile requires (Part 03 §5)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader.profile import parquet_floor
from escapewheel_validator.generate import adjacency_settles_uniqueness
from escapewheel_validator.shim.ordering import verify_order

from .arrow import schema, sort_key
from .encoding import encodings, inefficient
from .errors import (
    UsageError,
    UsageFault,
)


def parquet_options(
    resource_id: str,
    spec: Mapping[str, Any],
    out: pa.Schema,
    extra: Mapping[str, Any] | None = None,
    sample: pa.Table | pa.RecordBatch | None = None,
) -> dict[str, Any]:
    """Parquet settings for one resource.

    **No page index.** `ColumnIndex` and `OffsetIndex` would give per-page bounds and byte
    offsets, letting pages behave like the chunks inside a Zarr shard — but unlike a shard index,
    nothing obliges a reader to read one, and neither DuckDB nor pyarrow does. DuckDB says so
    outright (duckdb#2755, closed as "not supported… mostly improves point queries which is not
    what DuckDB is focused on") and measures identically with it and without; pyarrow prunes at
    row-group granularity too. arrow-rs, DataFusion and Spark would use it, and it costs little
    -- but a packet rebuilds from its recipe, so carrying an unexercised feature buys less than
    turning it on when a reader needs it. pyarrow defaults it off, which is where this leaves
    it. See `encoding.STREAMED_BATCH_ROWS` for the row-group half.

    `sorting_columns` is written for every table that declares an order. It costs nothing, and
    it is what lets a file state which of several possible orderings it is in rather than
    leaving a reader to infer it from statistics. It is only truthful because both write paths
    produce the declared order: the records path sorts in `arrow.build_table`, and the streaming path
    is checked by the validator's physical-order shim (Part 05 §5.3) before the commit completes.
    """
    options: dict[str, Any] = {"compression": "zstd", "data_page_version": "1.0"}
    # A caller may hand over a column as dictionary codes rather than decoding what Parquet is
    # about to re-encode. Parquet has no dictionary type -- the column is BYTE_ARRAY/String
    # either way -- so the only thing that would record the choice is the Arrow schema pyarrow
    # stores as metadata, and storing it would make the file advertise a type the registry does
    # not declare. Withhold it, and the file reads back as the registry says.
    if any(pa.types.is_dictionary(field.type) for field in out):
        options["store_schema"] = False
    delta, plain = encodings(resource_id, spec, out, extra, sample)
    if delta or plain:
        options["use_dictionary"] = [n for n in out.names if n not in {*delta, *plain}]
        if delta:
            options["column_encoding"] = dict.fromkeys(delta, "DELTA_BINARY_PACKED")
    keys = sort_key(resource_id, spec) or []
    if columns := [pq.SortingColumn(out.names.index(k)) for k in keys if k in out.names]:
        options["sorting_columns"] = columns
    return options


def check_parquet_floor(path: Path) -> None:
    """Refuse a packet-owned table whose footer exceeds the incorporated writer floor."""
    floor = parquet_floor()
    metadata = pq.ParquetFile(path).metadata
    compressions: set[str] = set()
    encodings: set[str] = set()
    for row_group in range(metadata.num_row_groups):
        group = metadata.row_group(row_group)
        for column in range(group.num_columns):
            chunk = group.column(column)
            compressions.add(str(chunk.compression).upper())
            encodings.update(str(value).upper() for value in chunk.encodings)
    outside_compression = sorted(compressions - set(floor["compressions"]))
    outside_encoding = sorted(encodings - set(floor["encodings"]))
    if outside_compression or outside_encoding:
        detail = []
        if outside_compression:
            detail.append(f"compression {outside_compression}")
        if outside_encoding:
            detail.append(f"encoding {outside_encoding}")
        raise UsageError(
            f"{path}: Parquet footer exceeds the portable writer floor: {', '.join(detail)}",
            code=UsageFault.PARQUET_FLOOR,
            where=str(path),
        )


#: Batches held ahead of the Parquet writer. Building a batch and encoding one cost about the
#: same, so serially a stream pays both and one worker ahead overlaps them. The depth is a
#: memory budget, not a throughput knob: one takes most of the available time, each further
#: batch held buys little for the memory it costs, and output is byte-identical at every depth.
PREFETCH = 1


def _prefetch(batches: Iterable[pa.RecordBatch], depth: int = PREFETCH) -> Iterator[pa.RecordBatch]:
    """Yield batches while the next is built on a worker thread.

    The producer's exception is re-raised in the consumer rather than lost in the thread, so a
    source that fails mid-stream still refuses the commit instead of truncating it silently.
    """
    queue: Queue[Any] = Queue(maxsize=depth)
    done = object()

    def produce() -> None:
        try:
            for batch in batches:
                queue.put(batch)
        except BaseException as exc:  # noqa: BLE001 - handed to the consumer, not swallowed
            queue.put(exc)
        else:
            queue.put(done)

    worker = Thread(target=produce, daemon=True)
    worker.start()
    try:
        while (item := queue.get()) is not done:
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        worker.join(timeout=0)


def _as_held(out: pa.Schema, held: pa.Schema) -> pa.Schema:
    """Take the registry's schema, but keep a column the caller already holds as codes.

    Decoding a dictionary here would only hand Parquet strings it is about to dictionary-encode
    again. The value type must still match what the registry declares; only the encoding is the
    caller's to choose.
    """
    fields = []
    for field in out:
        carried = held.field(field.name).type if field.name in held.names else None
        if carried is not None and pa.types.is_dictionary(carried) and carried.value_type == field.type:
            field = field.with_type(carried)
        fields.append(field)
    return pa.schema(fields)


def write_stream(
    spec: Mapping[str, Any],
    batches: Iterable[pa.RecordBatch],
    path: Path,
    resource_id: str,
    extra: Mapping[str, Any] | None = None,
    report: list[str] | None = None,
) -> int:
    """Write batches to Parquet one row group at a time, casting each to the registry schema.

    The first batch fixes the schema, exactly as the first record does on the records path:
    an optional column is emitted when something carries it. A later batch may omit a
    declared column -- it is written as nulls, like a record that lacks the key -- but may
    not introduce one the schema does not have, because that column would be dropped without
    a word.

    An empty stream writes nothing and leaves no file, matching the records path, where a
    resource with no rows is simply absent from the packet.

    Returns the rows written, which is the only count of a streamed table anything holds: a
    generator's length is not knowable before it has run.

    Each batch becomes exactly one row group, so the caller controls row-group boundaries as
    well as order. That is what lets `analysis.spike_events` keep every row group inside a
    single time bucket (Part 03 §5.4) — cutting at a fixed row count instead would let a group
    straddle two buckets and span twice the intended time range — and it is what lets a caller
    size row groups for the store the packet will live on.
    """
    writer: pq.ParquetWriter | None = None
    out: pa.Schema | None = None
    written = 0
    try:
        # Verified on the way in, not read back afterwards. The rows pass through here
        # already sorted by the source, so comparing them costs the comparison alone, where
        # establishing the same fact from the written file costs re-reading its sort columns.
        # It runs inside the producer thread, so the comparison overlaps the Parquet encoding
        # rather than adding to it. `commit` tells the validator which resources this settled; a
        # validator handed an unknown packet still reads every one.
        keys = sort_key(resource_id, spec) or []
        unique = spec["primary_key"] if keys and adjacency_settles_uniqueness(resource_id, spec) else None
        # Three stages, not two: building a batch, comparing it and encoding it cost about the
        # same, so folding the comparison into the producer would make it the bottleneck and
        # give back what skipping the re-read saves. A queue either side of it lets all three
        # run at once, and the slowest one sets the pace.
        for batch in _prefetch(_prefetch(verify_order(batches, keys, unique)) if keys else batches):
            first = out is None
            if out is None:
                out = _as_held(schema(spec, set(batch.schema.names)), batch.schema)
            if unexpected := sorted(set(batch.schema.names) - set(out.names)):
                # Two causes reach here and they send an author to different files: a column the
                # registry never declared, and an optional one the first batch lacked so `schema`
                # left it out. The check fires on the first batch too, where only the first is
                # possible, so a message naming only the second described the rarer case.
                declared = {c["name"] for c in spec["columns"]}
                said = []
                if undeclared := [n for n in unexpected if n not in declared]:
                    said.append(f"{undeclared} is declared by no registry this build loaded")
                if late := [n for n in unexpected if n in declared]:
                    said.append(f"{late} is optional and absent from the first batch")
                raise UsageError(
                    f"{resource_id}: {'; '.join(said)}; the column would be dropped silently",
                    code=UsageFault.UNDECLARED_COLUMN if undeclared else UsageFault.COLUMN_AFTER_FIRST_BATCH,
                    where=resource_id,
                )
            columns = [
                batch.column(name) if name in batch.schema.names else pa.nulls(batch.num_rows, field.type)
                for name, field in zip(out.names, out, strict=True)
            ]
            held = pa.record_batch(columns, schema=out)
            if first:
                # Chosen from the batch as it will be written, not as it arrived: a column the source
                # omits is written as nulls and counts as none, and a column cast to the registry's
                # type is measured at that type, where the source's can cost 77x as much plain.
                options = parquet_options(resource_id, spec, out, extra, held)
                writer = pq.ParquetWriter(path, out, **options)
                if report is not None:
                    report.extend(
                        inefficient(
                            resource_id,
                            pa.Table.from_batches([held]),
                            options.get("column_encoding", {}) and list(options["column_encoding"]) or [],
                            [
                                n
                                for n in out.names
                                if n not in options.get("use_dictionary", out.names)
                                and n not in options.get("column_encoding", {})
                            ],
                        )
                    )
            assert writer is not None
            # `row_group_size` is load-bearing, not decoration: left to pyarrow it defaults to
            # 2**20 rows and silently cuts a larger batch into several row groups, which would
            # break the boundary guarantee this docstring makes.
            writer.write_batch(held, row_group_size=batch.num_rows)
            written += batch.num_rows
    finally:
        if writer is not None:
            writer.close()
    return written


__all__ = ["check_parquet_floor", "parquet_options", "write_stream"]
