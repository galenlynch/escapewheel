"""What a build costs: one recipe imported at several source-worker counts, wall time and peak RSS.

Each cell runs the writer's `escapewheel import` as a child, from the writer project beside this
directory, into a fresh packet root under `--out-root`, and refuses a root that exists. Peak RSS
is the largest single process in the child's tree, from `wait4`; a delivering adapter's
subprocess counts if it outgrows the build. The writer stages beside the packet, so `--out-root`
is the scratch disk being measured, and `TMPDIR` is pointed there too. The source cache the
recipe names is shared by every cell, so run one build first if the cells should all find it warm.

    uv run python build.py --recipe /data/recipe.toml --out-root /nvme/bench/build \
        --workers 1 4 --json-out results/$(date +%F)-build-<session>.json
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import time
from pathlib import Path

import benchkit

WRITER = Path(__file__).resolve().parents[1] / "escapewheel-writer"
#: A source's turn, as the build logs it.
TURN = re.compile(r"^\[\s*([\d.]+)s\] (\S+) -> ")
#: The steps after the sources, with the time the writer reports for each.
STEPS = re.compile(r"^\[\s*([\d.]+)s\] (staged .*|derived .*|validated .*|promoted .*)$")


def timeline(log: str) -> dict:
    """When each source's turn began, and the steps after them, in seconds from the build's start."""
    turns, steps = {}, []
    for line in log.splitlines():
        if found := TURN.match(line):
            turns[found[2]] = float(found[1])
        elif found := STEPS.match(line):
            steps.append({"at_s": float(found[1]), "step": found[2]})
    return {"turns_s": turns, "steps": steps}


def cell(recipe: Path, out: Path, workers: int) -> dict:
    """Import `recipe` into `out` with `workers` sources open at once."""
    if out.exists():
        raise SystemExit(f"{out} exists; give each cell a fresh packet root")
    out.parent.mkdir(parents=True, exist_ok=True)
    log_path = out.parent / f"{out.name}.log"
    command = ["uv", "run", "-q", "--project", str(WRITER), "escapewheel", "import", str(recipe)]
    command += ["--out", str(out), "--source-workers", str(workers)]
    environment = dict(os.environ, TMPDIR=str(out.parent))
    with log_path.open("w") as log:
        clock = time.perf_counter()
        child = subprocess.Popen(
            command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=environment
        )
        _, status, usage = os.wait4(child.pid, 0)
        wall = time.perf_counter() - clock
    child.returncode = os.waitstatus_to_exitcode(status)
    text = log_path.read_text()
    return {
        "workers": workers,
        "out": str(out),
        "log": str(log_path),
        "exit": child.returncode,
        "wall_s": round(wall, 1),
        # Linux reports `ru_maxrss` in KiB.
        "peak_rss_gib": round(usage.ru_maxrss / 2**20, 2),
        "committed": (out / "packet.json").is_file(),
        **timeline(text),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--recipe", help="the recipe to import (env BENCH_RECIPE)")
    parser.add_argument("--out-root", help="directory the cells' packets go under (env BENCH_BUILD_ROOT)")
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 4], help="source-worker counts, one cell each")
    parser.add_argument("--label", default="build", help="prefix of each cell's packet directory")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    recipe = benchkit.required_path(args.recipe, "BENCH_RECIPE", "recipe")
    named_root = args.out_root or os.environ.get("BENCH_BUILD_ROOT")
    if not named_root:
        raise SystemExit("name the packet root with --out-root or BENCH_BUILD_ROOT")
    root = Path(named_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    cells = []
    for workers in args.workers:
        result = cell(recipe, root / f"{args.label}-w{workers}", workers)
        cells.append(result)
        print(
            f"workers {workers:>2}  wall {result['wall_s']:7.1f} s  peak RSS {result['peak_rss_gib']:6.2f} GiB"
            f"  exit {result['exit']}  committed {result['committed']}",
            flush=True,
        )
    benchkit.write_result(
        args.json_out,
        {"environment": benchkit.environment([recipe.parent, root]), "recipe": str(recipe), "cells": cells},
    )


if __name__ == "__main__":
    main()
