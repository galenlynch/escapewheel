"""Seconds to copy a session's stores from S3 to local disk or to RAM, the step before a warm read.

Many users copy a dataset before analysing it rather than read it over the network. A copy costs
its seconds once and every later read is local, so with the cold read times of `readers.py`,
`trials.py` and `population.py` it gives the number of analyses after which copying pays.

Each store is copied whole by a tool a user would reach for: `aws s3 cp --recursive`, with the
CLI's default ten concurrent requests, or `s5cmd cp`, which defaults to 256. A store under
`/dev/shm` is held in RAM. The destination is emptied before each run, and the store's bytes and
objects, and the bytes the host received, are recorded beside the seconds.

    uv run python download.py --store S3_URI [S3_URI ...] --dest DIR [--tool aws s5cmd] [--json-out results/x.json]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

import benchkit

TOOLS = ("aws", "s5cmd")


def command(tool: str, store: str, dest: Path, single: bool) -> list[str]:
    """The copy of one store, unsigned, since the stores measured are public."""
    if tool == "aws":
        return [
            "aws",
            "s3",
            "cp",
            "--no-sign-request",
            "--only-show-errors",
            *([] if single else ["--recursive"]),
            store,
            str(dest),
        ]
    source = store if single else store.rstrip("/") + "/*"
    return ["s5cmd", "--no-sign-request", "cp", source, f"{dest}/"]


def copy(tool: str, store: str, dest: Path) -> dict:
    """Copy one store into an emptied `dest`, and time it."""
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    single = benchkit.is_hdf5(store)
    before = benchkit.received_bytes()
    clock = time.perf_counter()
    done = subprocess.run(command(tool, store, dest, single), capture_output=True, text=True, check=False)
    seconds = time.perf_counter() - clock
    after = benchkit.received_bytes()
    if done.returncode:
        return {"error": (done.stderr.strip().splitlines() or ["no output"])[-1][:200]}
    files = [path for path in dest.rglob("*") if path.is_file()]
    return {
        "seconds": seconds,
        "bytes": sum(path.stat().st_size for path in files),
        "objects": len(files),
        "received_bytes": after - before if before is not None and after is not None else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--store", nargs="+", required=True, help="S3 URIs of packets, NWB-Zarr prefixes or NWB-HDF5 objects"
    )
    parser.add_argument(
        "--dest", type=Path, required=True, help="directory to copy into, emptied per run; /dev/shm for RAM"
    )
    parser.add_argument("--tool", nargs="+", default=list(TOOLS), choices=TOOLS)
    parser.add_argument("--repeat", type=int, default=1, help="runs per cell; the median is reported")
    parser.add_argument("--keep", action="store_true", help="leave the last copy in place")
    parser.add_argument("--json-out", type=Path, help="write the result here as JSON")
    args = parser.parse_args()
    # The stores are public, and a stale profile makes the CLI try to refresh a token first.
    for name in ("AWS_PROFILE", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        os.environ.pop(name, None)
    result = {"environment": benchkit.environment(args.store), "dest": str(args.dest), "cells": []}
    print(f"{'store':72s} {'tool':6s} {'seconds':>8s} {'GB':>7s} {'objects':>8s} {'MB/s':>7s}")
    for store in args.store:
        dest = args.dest / Path(store.rstrip("/")).name
        for tool in args.tool:
            runs = [copy(tool, store, dest) for _ in range(args.repeat)]
            good = sorted((run for run in runs if "error" not in run), key=lambda run: run["seconds"])
            cell = good[len(good) // 2] if good else runs[-1]
            result["cells"].append({"store": store, "tool": tool, "runs": len(good), **cell})
            if good:
                rate = cell["bytes"] / cell["seconds"] / 1e6
                text = f"{cell['seconds']:8.2f} {cell['bytes'] / 1e9:7.2f} {cell['objects']:8d} {rate:7.0f}"
            else:
                text = f"failed: {cell['error']}"
            print(f"{store[-72:]:72s} {tool:6s} {text}", flush=True)
        if not args.keep:
            shutil.rmtree(dest, ignore_errors=True)
    benchkit.write_result(args.json_out, result)


if __name__ == "__main__":
    main()
