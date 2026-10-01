"""Every byte of one `stream-v0.1` delivery, message by message.

`build_side.py` shows that the three protocols agree; this shows what the pipe actually carries —
the JSON a build hands over, then each resource as an Arrow IPC stream, then the reserved `end`
stream that says the delivery finished. Three resources rather than eighteen, so the trace fits on
a page, and one of them is a resource this session has nothing for.

    uv run --project ../../escapewheel-writer python stream_trace.py
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow as pa

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "escapewheel-writer"))
sys.path.insert(0, str(HERE.parent.parent / "escapewheel-writer/tests"))

import build_side
import nwbfixture
import serve_nwb
import serve_stream
from escapewheel_writer.sources.nwb import NWBSource

SESSION = "mini_2025-04-09"
#: The four bytes every Arrow IPC message opens with, and the eight that end a stream.
CONTINUATION = b"\xff\xff\xff\xff"
END_OF_STREAM = CONTINUATION + b"\x00\x00\x00\x00"


def context(root: Path) -> dict:
    """What a build holds for this adapter, before it narrows `wanted`."""
    return {
        "root": str(root),
        "reference_clock": {
            "clock_id": "harp",
            "session_id": SESSION,
            "origin": "HARP epoch",
            "tick_rate_num": 31_250,
            "tick_rate_den": 1,
            "metadata": {"label": "HARP"},
        },
        "session_id": SESSION,
    }


#: The recipe's options, which a declared name resolves against after the vocabulary.
OPTIONS = {"zone": "America/Los_Angeles", "interval_kind": "task.trials"}


def walk(raw: bytes) -> None:
    """Name every message in the delivery, with the offset it begins at."""
    # A pyarrow reader, not a BytesIO: `read_message` takes a native file.
    handle = pa.BufferReader(raw)
    schema: pa.Schema | None = None
    print(f"{'offset':>8}  {'message':<15} {'meta':>5} {'body':>7}  what it says")
    while handle.tell() < len(raw):
        at = handle.tell()
        if raw[at : at + 8] == END_OF_STREAM:
            handle.seek(at + 8)
            print(f"{at:>8}  {'end-of-stream':<15} {'-':>5} {'-':>7}  that resource is complete")
            schema = None
            continue
        message = pa.ipc.read_message(handle)
        body = len(message.body) if message.body is not None else 0
        kind = str(message.type)
        if kind == "schema":
            schema = pa.ipc.read_schema(message)
            resource = schema.metadata[b"resource_id"].decode()
            fields = ", ".join(schema.names) or "no fields"
            note = f"{resource}: {fields}"
        elif kind == "record batch":
            assert schema is not None, "a batch before its schema"
            note = f"{pa.ipc.read_record_batch(message, schema).num_rows} row(s)"
        else:
            note = ""
        print(f"{at:>8}  {kind:<15} {len(message.metadata):>5} {body:>7}  {note}")


def main() -> int:
    with tempfile.TemporaryDirectory(dir="/mnt/Data") as tmp:
        root = nwbfixture.build(Path(tmp))
        # Sorted: `PRODUCES` is a set, so its iteration order changes between processes and an
        # unsorted trace would not be the same trace twice.
        declares = sorted(NWBSource.PRODUCES)
        held = {**context(root), "wanted": declares}

        # Which resources this session has rows for, so the trace can carry one that has none.
        produced = serve_nwb.build(build_side.supply(serve_nwb.NEEDS, held, OPTIONS)).records()
        populated = [r for r in declares if produced.get(r)]
        empty = [r for r in declares if not produced.get(r)]
        held["wanted"] = [*populated[:2], empty[0]]
        supplied = build_side.supply(serve_nwb.NEEDS, held, OPTIONS)
        wire = json.dumps(supplied)

        print("1. what the build hands over\n")
        print(f"   argv[0] {sys.executable}")
        print(f"   argv[1] {HERE / 'serve_stream.py'}, and no argument beyond it")
        print(f"   stdin   {len(wire)} bytes of JSON, which is the whole of what crosses:")
        for term, value in supplied.items():
            print(f"           {term} = {json.dumps(value)[:84]}")
        print(f"\n   {len(held['wanted'])} resources asked for: {', '.join(held['wanted'])}")
        print(f"   {empty[0]} is one this session has no rows for\n")

        print("2. what comes back on standard output\n")
        child = subprocess.run(
            [sys.executable, str(HERE / "serve_stream.py")],
            input=wire.encode(),
            stdout=subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": str(HERE)},
            check=True,
        )
        raw = child.stdout
        print(f"   {len(raw)} bytes, exit {child.returncode}\n")
        walk(raw)

        print("\n3. what the build reads, one resource at a time\n")
        handle = io.BytesIO(raw)
        got, ended, ends = {}, False, []
        while handle.tell() < len(raw):
            reader = pa.ipc.open_stream(handle)
            resource = reader.schema.metadata[b"resource_id"].decode()
            if resource == serve_stream.SENTINEL:
                ended = True
                print(f"   {resource:34s} the sentinel, at byte {handle.tell()} of {len(raw)}")
                break
            table = reader.read_all()
            got[resource] = table
            ends.append(handle.tell())
            print(
                f"   {resource:34s} {table.num_rows:>5} rows, {table.num_columns:>2} columns, "
                f"handle now at {handle.tell()}"
            )
        print(
            f"\n   complete = {ended and set(got) == set(supplied['wanted'])}, "
            f"exit {child.returncode}: the run succeeded"
        )

        print("\n4. the same delivery, from a command killed after the second resource\n")
        died = raw[: ends[1]]
        walk(died)
        print(
            f"\n   {len(died)} bytes and no sentinel, so the build refuses the delivery and "
            f"names\n   {list(got)[1]} as the resource the adapter died after, "
            "rather than the first that never arrived"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
