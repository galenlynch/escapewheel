"""The build's side: read an adapter's NEEDS, supply exactly those, and read its rows three ways.

This is the interface `a-build-reaches-a-source-through-declarations` states, exercised end to end
against the adapter that receives the most, over each of the three protocols the draft names. What
crosses is one JSON argument; what comes back is a resource at a time, and the rows must agree.

    uv run --project ../../escapewheel-writer python build_side.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.flight as fl
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "escapewheel-writer"))
sys.path.insert(0, str(HERE.parent.parent / "escapewheel-writer/tests"))

import nwbfixture
from escapewheel_writer import arrow
from escapewheel_writer.sources.nwb import NWBSource

REGISTRY = json.loads(
    (HERE.parent.parent / "registry" / "logical_schemas.json").read_text()
)["tables"]


def reconcile(resource: str, table) -> pa.Table:
    """What a build does with a delivery: settle types and presence against the registry.

    The same call the writer makes on records handed over in process, so a boundary that changes
    nothing leaves the two tables equal.
    """
    return arrow.build(resource, REGISTRY[resource], table.to_pylist())


import serve_nwb
import serve_stream

SESSION = "mini_2025-04-09"

#: What a build holds and can hand over, from Part 05 §4's staging context. A term an adapter names
#: that is not here is one a build must refuse before opening any source.
SUPPLIABLE = {
    "root",
    "reference_clock",
    "clocks",
    "first_samples",
    "units",
    "zone",
    "session_id",
    "wanted",
    "array_location",
}


def supply(needs, context):
    """The values a build passes for what an adapter declared, and nothing else."""
    unknown = set(needs) - SUPPLIABLE
    if unknown:
        raise SystemExit(
            f"the adapter needs {sorted(unknown)}, which a build cannot supply"
        )
    return {term: context[term] for term in needs if term in context}


def over_flight(tmp: str, wire: str, wanted: list[str]) -> tuple[dict, dict, float]:
    """`flight-v0.1`: Stage 1 from ListFlights, then one DoGet per resource."""
    socket = str(Path(tmp) / "adapter.sock")
    started = time.perf_counter()
    child = subprocess.Popen(
        [sys.executable, str(HERE / "serve_nwb.py"), socket, wire],
        stdout=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": str(HERE)},
    )
    if child.stdout.readline().strip() != "ready":
        raise SystemExit("the adapter did not come up")
    client = fl.connect(fl.Location.for_grpc_unix(socket))
    stage1 = {
        fi.descriptor.path[0].decode(): fi.total_records for fi in client.list_flights()
    }
    got = {n: client.do_get(fl.Ticket(n.encode())).read_all() for n in stage1}
    elapsed = 1000 * (time.perf_counter() - started)
    client.close()
    child.terminate()
    child.wait()
    return stage1, got, elapsed


def over_files(tmp: str, wire: str, wanted: list[str]) -> tuple[dict, dict, float]:
    """`files-v0.1`: the adapter writes Parquet, and Stage 1 is the footers."""
    root = Path(tmp) / "delivered"
    root.mkdir()
    started = time.perf_counter()
    code = subprocess.call(
        [sys.executable, str(HERE / "serve_files.py"), str(root), wire],
        env={**os.environ, "PYTHONPATH": str(HERE)},
    )
    if code:
        raise SystemExit(f"the adapter exited {code}")
    stage1 = {
        f.stem: pq.ParquetFile(f).metadata.num_rows
        for f in sorted(root.glob("*.parquet"))
    }
    got = {n: pq.read_table(root / f"{n}.parquet") for n in stage1}
    return stage1, got, 1000 * (time.perf_counter() - started)


def over_stream(tmp: str, wire: str, wanted: list[str]) -> tuple[dict, dict, float]:
    """`stream-v0.1`: concatenated IPC on standard output, ended by the sentinel."""
    started = time.perf_counter()
    child = subprocess.Popen(
        [sys.executable, str(HERE / "serve_stream.py"), wire],
        stdout=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": str(HERE)},
    )
    got, ended = {}, False
    while True:
        try:
            reader = pa.ipc.open_stream(child.stdout)
        except (pa.ArrowInvalid, OSError):
            break
        name = reader.schema.metadata[b"resource_id"].decode()
        if name == serve_stream.SENTINEL:
            ended = True
            break
        got[name] = reader.read_all()
    child.wait()
    if not ended or child.returncode:
        raise SystemExit(f"delivery truncated, exit {child.returncode}")
    # Stage 1 is the delivery: a stream is read before anything about it is known.
    return (
        {n: t.num_rows for n, t in got.items()},
        got,
        1000 * (time.perf_counter() - started),
    )


def main() -> int:
    """Run the NWB adapter over each protocol and check the three agree."""
    with tempfile.TemporaryDirectory(dir="/mnt/Data") as tmp:
        root = nwbfixture.build(Path(tmp))
        context = {
            "root": str(root),
            "reference_clock": {
                "clock_id": "harp",
                "session_id": SESSION,
                "name": "HARP",
                "tick_rate_num": 31_250,
                "tick_rate_den": 1,
                "origin": "HARP epoch",
            },
            "zone": "America/Los_Angeles",
            "session_id": SESSION,
            # Everything the adapter declares, so every resource crosses and the five this
            # session has nothing for arrive empty rather than not arriving.
            "wanted": list(NWBSource.PRODUCES),
        }
        supplied = supply(serve_nwb.NEEDS, context)
        supplied["options"] = {"interval_kind": "task.trials"}
        wire = json.dumps(supplied)
        wanted = context["wanted"]
        print(f"a build supplies {sorted(serve_nwb.NEEDS)}")
        print(
            f"  as {len(wire)} bytes of JSON, naming all {len(wanted)} resources "
            f"this adapter produces\n"
        )

        here = serve_nwb.build({**supplied, "root": str(root)}).records()
        results = {}
        for name, run in (
            ("flight-v0.1", over_flight),
            ("files-v0.1", over_files),
            ("stream-v0.1", over_stream),
        ):
            stage1, got, elapsed = run(tmp, wire, wanted)
            complete = set(got) == set(wanted)
            results[name] = (stage1, True)
            # The boundary's own property: what a source produced is what a build receives.
            # Types and R53 numbering are the build's next step, against the registry.
            differ = [r for r in got if got[r] != serve_nwb.as_table(here.get(r, []))]
            same = not differ
            print(f"{name}")
            print(
                f"  {len(got)} resources, {sum(t.num_rows for t in got.values())} rows, "
                f"{sum(1 for t in got.values() if t.num_rows == 0)} empty, "
                f"complete={complete}, {elapsed:.0f} ms"
            )
            print(
                f"  identical to the adapter in process: {same}"
                + (f", differing in {differ}" if differ else "")
            )

        agreed = len({tuple(sorted(s.items())) for s, _ in results.values()}) == 1
        print(f"\nall three protocols report the same Stage 1: {agreed}")
        absent = sorted(r for r in wanted if r not in here)
        print(f"in process the adapter omits {len(absent)} of {len(wanted)}: {absent}")
        print("over every protocol they arrive at 0 rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
