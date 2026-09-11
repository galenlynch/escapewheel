"""The build's side: read an adapter's NEEDS, supply exactly those, and read its rows over Flight.

This is the interface `a-build-reaches-a-source-through-declarations` states, exercised end to end
against the adapter that receives the most. What crosses is a socket path and one JSON argument;
what comes back is a descriptor per resource and its rows.

    uv run --project ../../escapewheel-writer python build_side.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pyarrow.flight as fl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "escapewheel-writer"))
sys.path.insert(0, str(HERE.parent.parent / "escapewheel-writer/tests"))

import nwbfixture

import serve_nwb

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


def main() -> int:
    """Run the NWB adapter out of process and compare what comes back."""
    with tempfile.TemporaryDirectory() as tmp:
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
            # The fourth is one this session has nothing for, to see how its absence arrives.
            "wanted": [
                "core.sessions",
                "core.probes",
                "core.electrodes",
                "core.clock_anchors",
            ],
        }
        supplied = supply(serve_nwb.NEEDS, context)
        supplied["options"] = {"interval_kind": "task.trials"}
        wire = json.dumps(supplied)
        print(f"a build supplies {sorted(serve_nwb.NEEDS)}")
        print(
            f"  as {len(wire)} bytes of JSON, naming {len(context['wanted'])} of the 18 "
            f"resources this adapter produces\n"
        )

        socket = str(Path(tmp) / "adapter.sock")
        started = time.perf_counter()
        child = subprocess.Popen(
            [sys.executable, str(HERE / "serve_nwb.py"), socket, wire],
            stdout=subprocess.PIPE,
            text=True,
            env={**dict(__import__("os").environ), "PYTHONPATH": str(HERE)},
        )
        if child.stdout.readline().strip() != "ready":
            raise SystemExit("the adapter did not come up")

        client = fl.connect(fl.Location.for_grpc_unix(socket))
        offered = {
            fi.descriptor.path[0].decode(): fi.total_records
            for fi in client.list_flights()
        }
        print(f"Stage 1, before any rows move: {offered}")

        got = {
            name: client.do_get(fl.Ticket(name.encode())).read_all() for name in offered
        }
        elapsed = 1000 * (time.perf_counter() - started)
        print(
            f"fetched {len(got)} resource(s), {sum(t.num_rows for t in got.values())} rows, "
            f"{elapsed:.0f} ms including the adapter's process start\n"
        )

        here = serve_nwb.build({**supplied, "root": str(root)}).records()
        same = all(got[name].to_pylist() == here.get(name, []) for name in got)
        print(f"rows identical to the same adapter in process: {same}")
        absent = [r for r in context["wanted"] if r not in here]
        print(
            f"{absent} is not in this session, and in process the adapter omits it; "
            f"over the boundary it arrives at {got[absent[0]].num_rows} rows"
        )
        child.terminate()
        child.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
