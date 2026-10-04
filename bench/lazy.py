"""What lazy reading saves: one question asked eagerly and lazily of the same packet.

Each operation is answered twice, in a fresh process after the page cache is evicted, and both
arms must return the same value.

- `eager` reads the table the question touches whole into a `pyarrow.Table`, through
  `Packet.table` or `PacketSet.table`, and answers in memory.
- `lazy` narrows before reading: a Scanner with a pushed-down filter, a mapping over a batch
  stream, or a Dataset handed to DuckDB or Polars, which push their own filter into the scan.

The operations:

- `first rows` takes the first 10,000 spikes of `core.spike_events`: `Scanner.head` against a
  sliced table.
- `spikes per unit` counts every unit's spikes, batch by batch against a `group_by`.
- `rate on clock` maps every spike of `core.spike_events` onto the reference clock and counts
  spikes per second, through `on_clock` over a stream against over a table. Peak memory is the
  difference.
- `region window` is the spikes of one region's units in a 60 s window, in seconds: `where` and
  `tick_range` on the stored ticks, then `on_clock` and `seconds`, against mapping the whole table
  and filtering after.
- `one session` reads the spikes of one packet of a two-packet `PacketSet`: `session_key` as a
  constraint, which skips the other packet's files, against reading both and filtering.
- `duckdb window` and `polars window` count each unit's spikes in the window from
  `analysis.spike_events`, from `Packet.scan` against from a table read whole.

The region's units and the window are settled before any clock starts, so both arms answer the
same question from the same inputs. Either store may be an `s3://` URI; a remote cell records the
bytes the host received, so run nothing else on the network meanwhile.

    uv run python lazy.py --packet P [--other Q] [--json-out results/x.json]
    uv run python lazy.py --child ARM OPERATION --plan PLAN   # one cell, as JSON
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import warnings
from pathlib import Path

import benchkit

ARMS = ("eager", "lazy")
OPERATIONS = (
    "first rows",
    "spikes per unit",
    "rate on clock",
    "region window",
    "one session",
    "duckdb window",
    "polars window",
)
CORE = "core.spike_events"
ANALYSIS = "analysis.spike_events"
FIRST = 10_000

WINDOW_SQL = (
    "SELECT count(DISTINCT unit_id) AS units, count(*) AS spikes FROM spikes WHERE t_tick BETWEEN {lo} AND {hi}"
)


def per_second(ticks, plan: dict):
    """Spikes in each whole second after the time origin, as counts indexed by second."""
    import numpy as np

    return np.bincount((ticks.to_numpy() - plan["t_zero"]) // plan["rate"])


def summed(counts: list) -> tuple[int, int]:
    """Add per-batch bincounts of differing lengths; the value is (bins, spikes)."""
    import numpy as np

    total = np.zeros(max((len(c) for c in counts), default=0), dtype=np.int64)
    for count in counts:
        total[: len(count)] += count
    return int(np.count_nonzero(total)), int(total.sum())


def run(arm: str, plan: dict, operation: str) -> object:
    """One operation, eagerly or lazily."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    from escapewheel_reader import on_clock, open_packet, open_packets, seconds, tick_range, where

    eager = arm == "eager"
    packet = open_packet(plan["packet"])
    lo, hi = plan["window_tick"]
    if operation == "first rows":
        rows = packet.table(CORE).slice(0, FIRST) if eager else packet.scanner(CORE).head(FIRST)
        return pc.sum(rows["t_tick"]).as_py()
    if operation == "spikes per unit":
        if eager:
            counts = packet.table(CORE, columns=["unit_id"]).group_by("unit_id").aggregate([("unit_id", "count")])
            return counts.num_rows, pc.max(counts["unit_id_count"]).as_py()
        total = np.zeros(0, dtype=np.int64)
        for batch in packet.scanner(CORE, columns=["unit_id"]).to_batches():
            count = np.bincount(batch["unit_id"].to_numpy())
            total = np.pad(total, (0, max(0, len(count) - len(total))))
            total[: len(count)] += count
        return int(np.count_nonzero(total)), int(total.max())
    if operation == "rate on clock":
        if eager:
            mapped = on_clock(packet, packet.table(CORE, columns=["unit_id", "t_tick"]), resource_id=CORE)
            return summed([per_second(mapped["t_tick"], plan)])
        stream = on_clock(packet, packet.scanner(CORE, columns=["unit_id", "t_tick"]), resource_id=CORE)
        return summed([per_second(batch["t_tick"], plan) for batch in stream])
    if operation == "region window":
        units = plan["region_units"]
        if eager:
            mapped = on_clock(packet, packet.table(CORE, columns=["unit_id", "t_tick"]), resource_id=CORE)
            inside = pc.and_(
                pc.is_in(mapped["unit_id"], pa.array(units, pa.int32())), pc.greater_equal(mapped["t_tick"], lo)
            )
            found = seconds(packet, mapped.filter(pc.and_(inside, pc.less(mapped["t_tick"], hi))))
        else:
            narrowed = packet.scanner(
                CORE,
                columns=["unit_id", "t_tick"],
                filter=where(unit_id=units) & tick_range(packet, CORE, (lo, hi - 1)),
            )
            found = seconds(packet, on_clock(packet, narrowed, resource_id=CORE)).read_all()
        return found.num_rows, round(pc.sum(found["t_second"]).as_py(), 3)
    if operation == "one session":
        pair = open_packets([plan["other"], plan["packet"]])
        if eager:
            both = pair.table(CORE, columns=["unit_id", "t_tick", "session_key"])
            return both.filter(pc.equal(both["session_key"], 1)).num_rows
        return pair.table(CORE, columns=["unit_id", "t_tick"], session_key=1).num_rows
    if operation == "duckdb window":
        import duckdb

        spikes = packet.table(ANALYSIS, columns=["unit_id", "t_tick"]) if eager else packet.scan(ANALYSIS)
        con = duckdb.connect()
        con.register("spikes", spikes)
        return con.sql(WINDOW_SQL.format(lo=lo, hi=hi - 1)).fetchone()
    if operation == "polars window":
        import polars as pl

        spikes = (
            pl.from_arrow(packet.table(ANALYSIS, columns=["unit_id", "t_tick"])).lazy()
            if eager
            else pl.scan_pyarrow_dataset(packet.scan(ANALYSIS))
        )
        found = (
            spikes.filter(pl.col("t_tick").is_between(lo, hi - 1))
            .select(pl.col("unit_id").n_unique().alias("units"), pl.len().alias("spikes"))
            .collect()
        )
        return found["units"][0], found["spikes"][0]
    raise ValueError(operation)


def make_plan(packet_path: str, other: str | None, window: tuple[float, float], region: str) -> dict:
    """Settle, from the packet, every value a child would otherwise read before its clock starts."""
    from escapewheel_reader import open_packet

    packet = open_packet(packet_path)
    origin = packet.sql(
        "SELECT s.t_zero_tick AS t0, c.tick_rate_num AS num, c.tick_rate_den AS den "
        "FROM core_sessions s JOIN core_clocks c ON c.clock_id = s.reference_clock_id"
    ).to_pylist()[0]
    rate = origin["num"] // origin["den"]
    units = packet.sql(
        "SELECT DISTINCT link.unit_id FROM core_unit_electrodes link "
        f"JOIN core_electrode_coordinates c USING (session_id, electrode_id) WHERE c.region_label = '{region}'"
    )
    return {
        "packet": packet_path,
        "other": other,
        "region": region,
        "region_aws": os.environ.get("AWS_REGION", "us-west-2"),
        "t_zero": origin["t0"],
        "rate": rate,
        "window_tick": [origin["t0"] + round(offset * rate) for offset in window],
        "window_s": list(window),
        "region_units": sorted(units["unit_id"].to_pylist()),
    }


#: Modules imported before the clock starts: an import costs the same whatever the arm.
IMPORTS = ("escapewheel_reader", "numpy", "pyarrow.compute", "pyarrow.dataset", "pyarrow.fs", "duckdb", "polars")


def child(arm: str, operation: str, plan: dict) -> None:
    """One cold cell, printed as JSON."""
    warnings.filterwarnings("ignore")
    for module in IMPORTS:
        importlib.import_module(module)
    stores = [plan["packet"]] + ([plan["other"]] if plan["other"] else [])
    benchkit.cold_child(stores, lambda: run(arm, plan, operation))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--packet", help="packet directory or URI (else BENCH_PACKET)")
    parser.add_argument("--other", help="a second packet, for `one session`; without it that operation is skipped")
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=ARMS)
    parser.add_argument("--operations", nargs="+", default=list(OPERATIONS), choices=OPERATIONS)
    parser.add_argument(
        "--window",
        nargs=2,
        type=float,
        default=(100.0, 160.0),
        metavar=("FROM_S", "TO_S"),
        help="window in seconds after the packet's time origin",
    )
    parser.add_argument("--region", default="MD", help="region label for `region window`")
    parser.add_argument("--repeat", type=int, default=1, help="cold runs per cell; the median is reported")
    parser.add_argument("--memory-max", help="kill a cell at this size, such as 64G, rather than swap")
    parser.add_argument("--json-out", type=Path, help="write the result here as JSON")
    parser.add_argument("--child", nargs=2, metavar=("ARM", "OPERATION"), help=argparse.SUPPRESS)
    parser.add_argument("--plan", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child(*args.child, json.loads(args.plan))

    packet = benchkit.required_store(args.packet, "BENCH_PACKET", "the packet")
    plan = make_plan(packet, args.other, tuple(args.window), args.region)
    operations = [op for op in args.operations if op != "one session" or args.other]
    stores = [packet] + ([args.other] if args.other else [])
    result = {
        "environment": benchkit.environment(stores),
        "plan": plan,
        "core_version": benchkit.core_version(packet),
        "packet_bytes": benchkit.tree_bytes(packet),
        "cells": [],
    }
    print(f"packet {packet} (core {result['core_version']}, {result['packet_bytes'] / 1e9:.2f} GB)")
    print(f"window {args.window[0]:g}-{args.window[1]:g} s; {len(plan['region_units'])} units in {args.region}\n")
    remote = benchkit.is_remote(packet)
    print(f"{'operation':16s}" + "".join(f"{arm:>22s}" for arm in args.arms))
    for operation in operations:
        cells = []
        for arm in args.arms:
            runs = [
                benchkit.run_child(
                    [__file__, "--child", arm, operation, "--plan", json.dumps(plan)], memory_max=args.memory_max
                )
                for _ in range(args.repeat)
            ]
            good = sorted((run for run in runs if "error" not in run), key=lambda run: run["seconds"])
            cell = good[len(good) // 2] if good else runs[-1]
            cell = {"arm": arm, "operation": operation, "runs": len(good), **cell}
            result["cells"].append(cell)
            text = f"{'failed':>21s}"
            if good:
                text = f"{cell['seconds']:8.3f}s {cell['peak_mib']:7.0f}MiB"
                if remote and cell.get("received_bytes") is not None:
                    text = f"{cell['seconds']:7.2f}s {cell['received_bytes'] / 1e6:7.1f}MB"
            cells.append(text)
        print(f"{operation:16s}" + "".join(f"{text:>22s}" for text in cells), flush=True)
    print("\nwhat each returned, to show the arms were asked the same question:")
    for operation in operations:
        values = [
            cell.get("value", cell.get("error", "?"))[:21] for cell in result["cells"] if cell["operation"] == operation
        ]
        print(f"  {operation:14s}" + "".join(f"{value:>22s}" for value in values))
    benchkit.write_result(args.json_out, result)


if __name__ == "__main__":
    main()
