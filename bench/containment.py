"""Which block holds each trial: four ways to answer containment, at four scales.

Whether a nesting needs a stored parent key turns on what the lookup costs without one. Trials
are disjoint and blocks are contiguous runs of them, the shape a dynamic-foraging session has,
so the lookup is a range join, an ASOF join, or a binary search; the fourth arm reads the key a
stored column would hold. The smallest scale is a real session's 708 trials in 18 blocks, and the
larger ones keep its trials-per-block ratio. Every arm returns one block key per trial as an
array, so none is flattered by returning a count, and the arms must agree.

Synthetic, so it takes no packet.

    uv run python containment.py [--scales 708:18 10000:250 ...] [--threads 4]
"""

from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

import benchkit
import duckdb
import numpy as np
import pyarrow as pa

SCALES = ("708:18", "10000:250", "100000:2500", "1000000:25000")
ARMS = ("range join", "ASOF join", "searchsorted", "stored key")
NO_BLOCK = np.uint32(0xFFFFFFFF)


def synthesize(n_trials: int, n_blocks: int) -> tuple[pa.Table, pa.Table, pa.Table]:
    """Disjoint trials, blocks as contiguous runs of them, and the trials with the key stored."""
    gap, length = 5_750, 100_000
    start = np.arange(n_trials, dtype=np.int64) * (length + gap) + 361_751_245_672
    stop = start + length
    edges = np.linspace(0, n_trials, n_blocks + 1).astype(np.int64)
    owner = np.repeat(np.arange(n_blocks, dtype=np.uint32), np.diff(edges))
    trials = pa.table({"trial_key": np.arange(n_trials, dtype=np.uint32), "start_tick": start, "stop_tick": stop})
    blocks = pa.table(
        {
            "block_key": np.arange(n_blocks, dtype=np.uint32),
            "start_tick": start[edges[:-1]],
            "stop_tick": stop[edges[1:] - 1],
        }
    )
    return trials, blocks, trials.append_column("block_key", pa.array(owner))


def median_time(fn, repeats: int) -> tuple[float, np.ndarray]:
    """Median wall time of `repeats` calls, and the last call's result."""
    runs = []
    for _ in range(repeats):
        clock = time.perf_counter()
        out = fn()
        runs.append(time.perf_counter() - clock)
    return statistics.median(runs), out


def arms(con: duckdb.DuckDBPyConnection, blocks: pa.Table, trials: pa.Table) -> dict:
    """Each arm as a call returning the block key of every trial, in trial order."""
    starts, stops = blocks["start_tick"].to_numpy(), blocks["stop_tick"].to_numpy()
    keys, ticks = blocks["block_key"].to_numpy(), trials["start_tick"].to_numpy()

    def keys_of(query: str) -> np.ndarray:
        return con.sql(query).fetch_arrow_table()["block_key"].to_numpy()

    def searchsorted() -> np.ndarray:
        index = np.searchsorted(starts, ticks, side="right") - 1
        inside = (index >= 0) & (ticks <= stops[np.clip(index, 0, None)])
        return np.where(inside, keys[np.clip(index, 0, None)], NO_BLOCK)

    return {
        "range join": lambda: keys_of(
            "SELECT b.block_key FROM t JOIN b ON t.start_tick BETWEEN b.start_tick AND b.stop_tick ORDER BY t.trial_key"
        ),
        # The most recent block start at or before the trial, then one comparison for a gap.
        "ASOF join": lambda: keys_of(
            "SELECT b.block_key FROM t ASOF JOIN b ON t.start_tick >= b.start_tick "
            "WHERE t.start_tick <= b.stop_tick ORDER BY t.trial_key"
        ),
        "searchsorted": searchsorted,
        "stored key": lambda: keys_of("SELECT block_key FROM s ORDER BY trial_key"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scales", nargs="+", default=list(SCALES), metavar="TRIALS:BLOCKS")
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=ARMS)
    parser.add_argument("--threads", type=int, default=4, help="DuckDB threads")
    parser.add_argument("--repeat", type=int, default=5, help="runs per cell; the median is reported")
    parser.add_argument("--json-out", type=Path, help="write the result here as JSON")
    args = parser.parse_args()

    result = {"environment": benchkit.environment([Path.cwd()]), "threads": args.threads, "cells": []}
    print(f"median of {args.repeat}, DuckDB at {args.threads} threads\n")
    print(f"{'trials':>9} {'blocks':>7} |" + "".join(f"{arm:>14s}" for arm in args.arms))
    for scale in args.scales:
        n_trials, n_blocks = (int(part) for part in scale.split(":"))
        trials, blocks, stored = synthesize(n_trials, n_blocks)
        con = duckdb.connect()
        con.execute(f"SET threads={args.threads}")
        for name, table in (("t", trials), ("b", blocks), ("s", stored)):
            con.register(name, table)
        calls = arms(con, blocks, trials)
        expected = stored["block_key"].to_numpy()
        texts = []
        for arm in args.arms:
            seconds, got = median_time(calls[arm], args.repeat)
            if not np.array_equal(got, expected):
                raise SystemExit(f"{arm} disagrees with the stored key at {scale}")
            result["cells"].append({"trials": n_trials, "blocks": n_blocks, "arm": arm, "seconds": seconds})
            texts.append(f"{seconds * 1e3:>11.2f} ms")
        con.close()
        print(f"{n_trials:>9,} {n_blocks:>7,} |" + "".join(texts))
    benchkit.write_result(args.json_out, result)


if __name__ == "__main__":
    main()
