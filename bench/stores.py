"""What finding a stored session and copying it to a compute node cost, counted in objects.

Before anything reads a dataset something lists it, and before a job runs on a node something
copies it there. Both are paid per object, which is where a packet's few Parquet files and an
NWB-Zarr's many chunks stop being comparable. Each root is listed once by its own known prefix,
then downloaded with `s5cmd` into a fresh directory that is removed afterwards.

    uv run python stores.py --root "776259 packet=s3://.../packet" --root "776259 nwb=s3://.../x.nwb" \\
        --stage-dir /nvme/bench/stage [--json-out results/x.json]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import benchkit


def listing(uri: str) -> tuple[float, int, int]:
    """One listing of a root: seconds, objects and bytes."""
    clock = time.perf_counter()
    objects = benchkit.store_objects(uri)
    return time.perf_counter() - clock, len(objects), sum(size for _, size in objects)


def stage(uri: str, under: Path) -> tuple[float, int]:
    """Download a root into a fresh directory, as a job would before it runs: seconds and bytes."""
    target = Path(tempfile.mkdtemp(dir=under, prefix="stage-"))
    try:
        clock = time.perf_counter()
        subprocess.run(
            ["s5cmd", "--numworkers", "64", "cp", f"{uri}/*", f"{target}/"], capture_output=True, text=True, check=True
        )
        elapsed = time.perf_counter() - clock
        return elapsed, benchkit.tree_bytes(target)
    finally:
        shutil.rmtree(target, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", action="append", required=True, metavar="NAME=URI", help="a store root to measure")
    parser.add_argument("--stage-dir", help="local directory to download into (else BENCH_STAGE)")
    parser.add_argument("--json-out", type=Path, help="write the result here as JSON")
    args = parser.parse_args()
    if shutil.which("s5cmd") is None:
        sys.exit("s5cmd is not on PATH")
    roots = dict(root.split("=", 1) for root in args.root)
    if not all(benchkit.is_remote(uri) for uri in roots.values()):
        sys.exit("every root is a store URI")
    under = benchkit.required_path(args.stage_dir, "BENCH_STAGE", "the stage directory")
    result = {"environment": benchkit.environment([*roots.values(), under]), "roots": []}
    print(f"{'root':16s}{'list':>9s}{'objects':>9s}{'GB':>8s}{'download':>10s}{'MB/s':>8s}")
    for name, uri in roots.items():
        listed, objects, size = listing(uri)
        staged, fetched = stage(uri, under)
        result["roots"].append(
            {
                "name": name,
                "uri": uri,
                "list_seconds": listed,
                "objects": objects,
                "bytes": size,
                "stage_seconds": staged,
                "staged_bytes": fetched,
            }
        )
        rate = fetched / 1e6 / staged
        print(f"{name:16s}{listed:8.2f}s{objects:9,}{size / 1e9:8.3f}{staged:9.2f}s{rate:8.1f}")
    benchkit.write_result(args.json_out, result)


if __name__ == "__main__":
    main()
