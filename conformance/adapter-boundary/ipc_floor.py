"""Which of Arrow IPC's choices a delivery may make, and what each costs.

`stream-v0.1` says rows cross as Arrow IPC, which names a family: a body may be compressed, a
stream may be written at either of two metadata versions, and a dictionary may be sent as a delta
against one already sent. Part 03 §5.5 pins the equivalent choices for stored Parquet, and this
measures what pinning them here costs an adapter and buys a build.

    uv run --project ../../escapewheel-writer python ipc_floor.py
"""

from __future__ import annotations

import io
import os
import time

import numpy as np
import pyarrow as pa

SPIKES = 5_000_000


def stream(table: pa.Table, resource_id: str = "core.units", **options) -> bytes:
    """One resource as a complete IPC stream, written with the options under test."""
    sink = pa.BufferOutputStream()
    table = table.replace_schema_metadata({"resource_id": resource_id})
    with pa.ipc.new_stream(sink, table.schema, options=pa.ipc.IpcWriteOptions(**options)) as writer:
        writer.write_table(table)
    return sink.getvalue().to_pybytes()


def through_pipe(table: pa.Table, **options) -> float:
    """Milliseconds to write a table into a pipe and read it back in another process."""
    read_fd, write_fd = os.pipe()
    started = time.perf_counter()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        opts = pa.ipc.IpcWriteOptions(**options)
        with (
            os.fdopen(write_fd, "wb") as fh,
            pa.ipc.new_stream(fh, table.schema, options=opts) as w,
        ):
            w.write_table(table)
        os._exit(0)
    os.close(write_fd)
    with os.fdopen(read_fd, "rb") as fh:
        pa.ipc.open_stream(fh).read_all()
    os.waitpid(pid, 0)
    return 1000 * (time.perf_counter() - started)


def spikes() -> pa.Table:
    """A spike-shaped table: the largest thing an adapter streams, and all integers."""
    rng = np.random.default_rng(0)
    return pa.table(
        {
            "unit_id": pa.array(rng.integers(0, 700, SPIKES, dtype=np.int32)),
            "t_tick": pa.array(np.sort(rng.integers(0, 2**31, SPIKES)).astype(np.int64)),
        }
    )


def main() -> None:
    print("what the write options offer")
    defaults = pa.ipc.IpcWriteOptions()
    print(f"  fields: {', '.join(f for f in dir(defaults) if not f.startswith('_'))}")
    print(f"  metadata_version defaults to {defaults.metadata_version!r}")

    print(f"\ncompression, {SPIKES} spike-shaped rows through a real pipe")
    table = spikes()
    for label, options in (
        ("uncompressed", {}),
        ("lz4", {"compression": "lz4"}),
        ("zstd", {"compression": "zstd"}),
    ):
        size = len(stream(table, **options))
        print(f"  {label:12s} {size / 1e6:6.1f} MB  {through_pipe(table, **options):5.0f} ms")

    print("\nconcatenation: where each stream leaves the handle")
    small = pa.table({"a": [1, 2, 3]})
    raw = stream(small) + stream(small.rename_columns(["b"]), "core.probes")
    handle, seen = io.BytesIO(raw), []
    while handle.tell() < len(raw):
        reader = pa.ipc.open_stream(handle)
        rows = reader.read_all().num_rows
        seen.append(f"{reader.schema.metadata[b'resource_id'].decode()} ({rows} rows) → {handle.tell()}")
    print(f"  {len(raw)} bytes: {'; '.join(seen)}")

    print("\nthe same bytes with one end-of-stream marker removed")
    unterminated = stream(small)[:-8] + stream(small.rename_columns(["b"]), "core.probes")
    try:
        pa.ipc.open_stream(pa.py_buffer(unterminated)).read_all()
        print("  read clean, which would make a lost marker invisible")
    except OSError as err:
        print(f"  {type(err).__name__}: {err}")

    print("\na dictionary-encoded column, which adds a message kind to the stream")
    coded = pa.table({"quality": pa.array(["sua", "mua", "sua"]).dictionary_encode()})
    raw = stream(coded) + stream(small)
    handle = io.BytesIO(raw)
    first = pa.ipc.open_stream(handle)
    print(f"  {len(stream(coded))} bytes, type {first.schema.field(0).type}, {first.read_all().num_rows} rows")
    print(f"  the stream after it still opens: {pa.ipc.open_stream(handle).read_all().num_rows} rows")


if __name__ == "__main__":
    main()
