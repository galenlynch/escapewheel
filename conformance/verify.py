"""Run every generator and every check in the monorepo, and fail on the first thing that is off.

There was no single command for this. The chain is reproducible — `registry/build.py` writes
`logical_schemas.json`, `tables.md` and the registry README; `fixtures/build.py` writes the
conformance corpus; the prototype writes its own packets — but reproducibility nobody runs is a
claim rather than a property, and three artifacts drifted for many revisions without anything
noticing: the corpus stopped building at R54, the prototype's registry left R2's format at R48,
and the registry README's counts were wrong in five places at once.

The load-bearing stage is **regenerate, then demand a clean tree**. Every generated file is
committed, so re-running the generators must change nothing; a diff means what is committed is
not what the code produces, which is the failure the other checks cannot see.

Usage:

    python verify.py            # every stage
    python verify.py --quick    # skip the test suites, which dominate the runtime
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Packages whose venv `uv run --project` resolves. The writer's is used for anything needing
#: pyarrow and duckdb outside a package, because it depends on all three.
TOOLS = ROOT / "nwb-lake-writer"

#: Each stage: what it is, where it runs, and what to run. A stage fails on a non-zero exit.
STAGES: list[tuple[str, Path, list[str]]] = [
    ("registry: generate", ROOT / "registry", [sys.executable, "build.py"]),
    ("registry: structural checks", ROOT / "registry",
     ["uv", "run", "--project", str(TOOLS), "python", "check.py"]),
    ("prototype: write packets", ROOT / "prototype/registry-codegen",
     ["uv", "run", "--project", str(TOOLS), "python", "fixture.py"]),
    ("prototype: conforming packet is clean", ROOT / "prototype/registry-codegen",
     ["uv", "run", "--project", str(TOOLS), "python", "validate.py", "packets/valid"]),
    ("corpus: write 26 packets", ROOT / "fixtures",
     ["uv", "run", "--project", str(TOOLS), "python", "build.py"]),
    ("corpus: every packet behaves as specified", ROOT / "fixtures",
     ["uv", "run", "--project", str(TOOLS), "python", "corpus.py"]),
]

#: Run after the generators, never before: a suite passing against stale generated input says
#: nothing. Skipped by --quick, since they are most of the runtime.
SUITES = ("nwb-lake-reader", "nwb-lake-validator", "nwb-lake-writer")

#: Repositories whose working tree must be clean once the generators have run. Only the ones
#: holding generated output; a package with an unrelated edit in progress is not this tool's
#: business.
GENERATED = ("registry", "prototype", "fixtures")


def run(cwd: Path, argv: list[str]) -> tuple[bool, str]:
    """Run one stage, returning whether it passed and its last line of output.

    `TMPDIR` is dropped. The project points scratch at `/mnt/Data` to keep large temporary files
    out of a tmpfs the memory cap cannot hold, and that mount forces root ownership, which pytest
    refuses to write a basetemp into. A caller who has exported it for a build should not have
    the suites fail for it.
    """
    env = {k: v for k, v in os.environ.items() if k != "TMPDIR"}
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False, env=env)
    tail = (done.stdout or done.stderr).strip().splitlines()
    return done.returncode == 0, tail[-1] if tail else ""


def clean(repo: str) -> list[str]:
    """Return the paths a repository reports as modified, which after generation must be none."""
    done = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT / repo,
                          capture_output=True, text=True, check=False)
    return [line for line in done.stdout.splitlines() if line.strip()]


def main() -> int:
    """Run every stage in order, reporting each, and return non-zero on any failure."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--quick", action="store_true", help="skip the test suites")
    args = parser.parse_args()

    stages = list(STAGES)
    if not args.quick:
        stages += [(f"{p}: tests", ROOT / p, ["uv", "run", "pytest", "-q"]) for p in SUITES]

    failed = []
    for name, cwd, argv in stages:
        clock = time.perf_counter()
        passed, tail = run(cwd, argv)
        print(f"{'ok  ' if passed else 'FAIL'} {name:46s} {time.perf_counter() - clock:5.1f}s  {tail[:60]}")
        if not passed:
            failed.append(name)

    # The one thing no stage above can report: whether what is committed is what the code
    # produces. Every generator has just run, so any diff is drift.
    for repo in GENERATED:
        if dirty := clean(repo):
            failed.append(f"{repo}: generated output differs from what is committed")
            print(f"FAIL {repo}: regenerating changed {len(dirty)} tracked file(s)")
            for line in dirty[:10]:
                print(f"       {line}")
        else:
            print(f"ok   {repo}: regenerating changed nothing")

    print()
    if failed:
        print(f"{len(failed)} stage(s) failed:")
        for name in failed:
            print(f"  {name}")
        return 1
    print(f"all {len(stages) + len(GENERATED)} stages passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
