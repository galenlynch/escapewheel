"""What a failure carries over `stream-v0.1`, where `failures.py` measures `flight-v0.1`.

Rows travel on standard output as concatenated Arrow IPC streams, one per resource, so a command
that dies partway leaves a build holding whatever arrived before it stopped. Flight discards a
partial transfer; this measures whether a stream does.

    uv run --project ../../escapewheel-writer python stream_failures.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pyarrow as pa

HERE = Path(__file__).resolve().parent
TABLES = {
    "core.sessions": pa.table({"session_id": pa.array([0], "int32")}),
    "core.units": pa.table(
        {"unit_id": pa.array([1, 2, 3, 4], "int32"), "quality": pa.array(["sua"] * 4)}
    ),
    "core.intervals": pa.table({"start_tick": pa.array([10, 20], "int64")}),
}


def encode(resource_id: str, table: pa.Table, batch_rows: int = 2) -> bytes:
    """One resource as a complete IPC stream, ending with its end-of-stream marker."""
    table = table.replace_schema_metadata({"resource_id": resource_id})
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        for batch in table.to_batches(max_chunksize=batch_rows):
            writer.write_batch(batch)
    return sink.getvalue().to_pybytes()


def emit(mode: str) -> None:
    """The adapter side: write rows to standard output and stop where the mode says."""
    out = sys.stdout.buffer
    streams = {r: encode(r, t) for r, t in TABLES.items()}
    out.write(streams["core.sessions"])
    if mode == "between":
        out.flush()
        raise SystemExit("the source file ended after core.sessions")
    if mode == "midbatch":
        # Everything but the end-of-stream marker: the schema and both batches arrived.
        out.write(streams["core.units"][:-8])
        out.flush()
        raise SystemExit("killed while writing core.units")
    if mode == "truncated":
        # Stopped inside a message, the shape a process killed mid-write leaves.
        out.write(streams["core.units"][: len(streams["core.units"]) // 2])
        out.flush()
        raise SystemExit("killed inside a core.units batch")
    for name in ("core.units", "core.intervals"):
        out.write(streams[name])
    out.flush()


def read(stdout) -> tuple[dict[str, int], str | None]:
    """Read the concatenation the way a build must, keeping what arrived before any failure."""
    got: dict[str, int] = {}
    while True:
        try:
            reader = pa.ipc.open_stream(stdout)
        except (pa.ArrowInvalid, OSError) as err:
            message = str(err).splitlines()[0]
            return got, None if "Expected to read" in message and not got else message
        except StopIteration:
            return got, None
        name = reader.schema.metadata[b"resource_id"].decode()
        got[name] = 0
        try:
            for batch in reader:
                got[name] += batch.num_rows
        except (pa.ArrowInvalid, OSError) as err:
            return got, str(err).splitlines()[0]


def run(mode: str):
    """One adapter, read off the pipe, returning what the build holds and why it stopped."""
    child = subprocess.Popen(
        [sys.executable, str(HERE / "stream_failures.py"), "emit", mode],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    got, error = read(child.stdout)
    child.wait()
    return got, error, child.returncode, child.stderr.read().decode()


def main() -> int:
    """Measure every mode and print what a build is left holding."""
    whole = sum(t.num_rows for t in TABLES.values())
    got, error, code, _ = run("clean")
    print(
        f"**A run that finishes.** {sum(got.values())} of {whole} rows, exit {code}, "
        f"parse error {error}\n"
    )

    got, error, code, stderr = run("between")
    print(
        "**The command dies between two resources.** The first is complete and valid:"
    )
    print(f"  the build holds {got}, exit {code}, parse error {error}")
    print(f"  standard error: {stderr.strip().splitlines()[-1]!r}\n")

    got, error, code, _ = run("midbatch")
    print("**The command dies after the rows and before the end-of-stream marker.**")
    print(f"  the build holds {got}, exit {code}")
    print(f"  parse error: {error}\n")

    got, error, code, _ = run("truncated")
    print(
        "**The command is killed inside a batch.** What had already been decoded stays decoded:"
    )
    print(f"  the build holds {got}, exit {code}")
    print(f"  parse error: {error}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "emit":
        emit(sys.argv[2])
    else:
        raise SystemExit(main())
