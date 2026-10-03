"""Regenerate the renderings and run the checks a change needs before it is committed.

`verify.py` is the authority; this command runs the steps around it that a contributor otherwise
types by hand, each in the uv project its tool belongs to, and prints one line per step.

    uv run --project escapewheel-writer python tools/gate.py             # quick
    uv run --project escapewheel-writer python tools/gate.py --changed   # quick, plus the touched suites
    uv run --project escapewheel-writer python tools/gate.py --full      # the full verifier

Quick regenerates the heading record and the single-file rendering, checks citations, the ledger
and the open revision stages, then runs `verify.py --quick`. `--changed [BASE]` adds the suite of
every package that differs from BASE (default: the merge-base with `main`, plus uncommitted
changes) and of every package depending on one, read from each project's path sources. `--full`
runs the runtime-capability preflight and, only if it passes, the full verifier.

Steps run with stdin closed and the caller's environment, so `UV_CACHE_DIR` carries through.
`GATE_TMPDIR` or `--tmpdir` sets `TMPDIR` for every step, for a machine whose `/tmp` is memory.
Complete output goes to a log whose path is printed last.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import verify

#: The integration suite runs in the writer's environment, so it depends on what the writer does.
INTEGRATION = ROOT / "integration"


@dataclass(frozen=True)
class Step:
    """One gate step, which fails on a non-zero exit."""

    name: str
    project: Path
    argv: tuple[str, ...]
    cwd: Path = ROOT


def quick_steps() -> list[Step]:
    """Return the steps every mode but `--full` runs, in order."""
    tree, writer = verify.TREE, verify.WRITER
    return [
        Step("headings recorded", tree, ("python", "headings.py"), tree),
        Step("single-file rendering", tree, ("python", "combine.py"), tree),
        Step("citations resolve", writer, ("python", "revisions/check_citations.py")),
        Step("ledger disposes every clause", writer, ("python", "revisions/ledger.py", "--summary")),
        Step("open revision stages", writer, ("python", "revisions/stages.py")),
        Step("verify --quick", writer, ("python", "verify.py", "--quick")),
    ]


def _path_sources(project: Path) -> set[Path]:
    """Return the in-repository projects `project` depends on by path."""
    document = tomllib.loads((project / "pyproject.toml").read_text())
    sources = document.get("tool", {}).get("uv", {}).get("sources", {})
    return {(project / source["path"]).resolve() for source in sources.values() if "path" in source}


def suite_dependencies() -> dict[Path, set[Path]]:
    """Map each suite's directory to every project directory it depends on, itself included."""
    direct = {stage.cwd: _path_sources(stage.project) | {stage.project} for stage in verify.SUITES}
    closure: dict[Path, set[Path]] = {}
    for suite, needs in direct.items():
        reached, frontier = {suite}, set(needs)
        while frontier:
            project = frontier.pop()
            if project not in reached:
                reached.add(project)
                frontier |= _path_sources(project) if (project / "pyproject.toml").exists() else set()
        closure[suite] = reached
    return closure


def changed_paths(base: str) -> list[Path]:
    """Return the files differing from `base`, committed or not, as absolute paths."""
    names: set[str] = set()
    for argv in (["git", "diff", "--name-only", base], ["git", "ls-files", "--others", "--exclude-standard"]):
        listed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=True)
        names |= {line for line in listed.stdout.splitlines() if line}
    return [ROOT / name for name in sorted(names)]


def suites_for(paths: list[Path]) -> list[verify.Stage]:
    """Return the suites whose package, or a package they depend on, contains a changed path."""
    dependencies = suite_dependencies()
    return [
        stage
        for stage in verify.SUITES
        if any(path.is_relative_to(project) for path in paths for project in dependencies[stage.cwd])
    ]


def _merge_base() -> str:
    """Return the merge-base of HEAD with `main`."""
    found = subprocess.run(["git", "merge-base", "HEAD", "main"], cwd=ROOT, capture_output=True, text=True, check=True)
    return found.stdout.strip()


def run(step: Step, env: dict[str, str], log: TextIO) -> bool:
    """Run one step, appending its output to `log`, print its one-line result, and return whether it passed."""
    clock = time.perf_counter()
    argv = ["uv", "run", "-q", "--project", str(step.project), *step.argv]
    done = subprocess.run(
        argv,
        cwd=step.cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log.write(f"==> {step.name}: {' '.join(argv)} (in {step.cwd})\n{done.stdout}\n")
    lines = done.stdout.strip().splitlines()
    last = lines[-1].strip() if lines else ""
    print(
        f"{'ok  ' if done.returncode == 0 else 'FAIL'} {step.name:32s} {time.perf_counter() - clock:6.1f}s  {last[:90]}"
    )
    return done.returncode == 0


def main() -> int:
    """Run the requested mode and return non-zero if any step failed."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--full", action="store_true", help="run the runtime preflight, then the full verifier")
    mode.add_argument(
        "--changed",
        nargs="?",
        const="",
        metavar="BASE",
        help="also run each touched package's suite (default BASE: the merge-base with main)",
    )
    parser.add_argument("--tmpdir", default=os.environ.get("GATE_TMPDIR"), help="TMPDIR for every step")
    args = parser.parse_args()

    env = dict(os.environ)
    if args.tmpdir:
        Path(args.tmpdir).mkdir(parents=True, exist_ok=True)
        env["TMPDIR"] = args.tmpdir
    descriptor, log_name = tempfile.mkstemp(prefix="escapewheel-gate-", suffix=".log", dir=args.tmpdir)

    with os.fdopen(descriptor, "w") as log:
        if args.full:
            preflight = Step("runtime capabilities", verify.WRITER, ("python", "tools/runtime_capabilities.py"))
            if not run(preflight, env, log):
                print(
                    "this environment cannot run the full verifier; rerun the same command with unrestricted "
                    "execution rather than retrying here, or use the quick gate"
                )
                print(f"log: {log_name}")
                return 1
            steps = [Step("verify (full)", verify.WRITER, ("python", "verify.py", "--stage-timeout", "1200"))]
        else:
            steps = quick_steps()
            if args.changed is not None:
                base = args.changed or _merge_base()
                suites = suites_for(changed_paths(base))
                print(f"changed since {base[:12]}: {', '.join(s.name for s in suites) or 'no package suite'}")
                steps += [Step(s.name, s.project, s.command, s.cwd) for s in suites]
        passed = [run(step, env, log) for step in steps]

    status = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True)
    if status.stdout.strip():
        print(status.stdout.rstrip())
    print(f"{'passed' if all(passed) else 'FAILED'}: {sum(passed)} of {len(passed)} steps; log: {log_name}")
    return 0 if all(passed) else 1


if __name__ == "__main__":
    sys.exit(main())
