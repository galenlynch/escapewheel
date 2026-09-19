"""Run every generator and every check in the monorepo.

The chain is reproducible — `registry/build.py` writes
`logical_schemas.json`, `tables.md` and the registry README; `fixtures/build.py` writes the
conformance corpus; the prototype writes its own packets — but reproducibility nobody runs is a
claim rather than a property, and three artifacts drifted for many revisions without anything
noticing: the corpus stopped building at R54, the prototype's registry left R2's format at R48,
and the registry README's counts were wrong in five places at once.

The load-bearing stage is **regenerate, then demand an unchanged candidate tree**. The candidate
may already contain intentional generated changes, so the verifier snapshots their content before
generation and compares it afterward. A change during verification means the candidate was stale
or a generated file had been edited by hand. Comparing to ``HEAD`` instead would make this command
incapable of passing before the very commit it is meant to check.

Usage:

    python verify.py            # every stage; package suites dominate the runtime
    python verify.py --quick    # skip the test suites, which dominate the runtime
    python verify.py --stage-timeout 60  # bound each individual stage
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

#: Packages whose venv `uv run --project` resolves. The writer's is used for anything needing
#: pyarrow and duckdb outside a package, because it depends on all three.
TOOLS = ROOT / "escapewheel-writer"

#: Each stage: what it is, where it runs, and what to run. A stage fails on a non-zero exit.
STAGES: list[tuple[str, Path, list[str]]] = [
    ("registry: generate", ROOT / "registry", [sys.executable, "build.py"]),
    ("root: the documents' counts are current", ROOT, [sys.executable, "facts.py"]),
    (
        "revisions: open stages are structurally complete",
        ROOT,
        [sys.executable, "revisions/stages.py"],
    ),
    (
        "revisions: process tooling tests",
        ROOT,
        [sys.executable, "-m", "unittest", "revisions.test_evidence"],
    ),
    (
        "revisions: process semantics tests",
        ROOT,
        [sys.executable, "revisions/test_process.py"],
    ),
    (
        "revisions: accepted evidence manifests resolve",
        ROOT,
        [sys.executable, "revisions/evidence.py"],
    ),
    (
        "registry: structural checks",
        ROOT / "registry",
        ["uv", "run", "--project", str(TOOLS), "python", "check.py"],
    ),
    (
        "citations: every one resolves, and no part number repeats",
        ROOT / "revisions",
        [sys.executable, "check_citations.py", "--quiet"],
    ),
    # The current-owner rule in `revisions/CONTRIBUTING.md#ew-citation-context`: a citation of a clause that landed in a part resolves
    # perfectly while still sending a reader to the change record, so nothing else can see it.
    (
        "citations: a requirement names its part",
        ROOT / "revisions",
        [sys.executable, "repoint.py", "--quiet"],
    ),
    (
        "citations: every exemption is still needed",
        ROOT / "revisions",
        [sys.executable, "repoint.py", "--exempt"],
    ),
    # A ratchet for undisposed clauses and exact current-owner and JSON targets.
    (
        "spec: every revision clause has a disposition",
        ROOT / "revisions",
        [sys.executable, "ledger.py", "--summary"],
    ),
    # The other half of what a citation needs. `check_citations.py` resolves a number and this
    # records what the number is about, so a section that keeps one and changes the other cannot
    # leave its citers resolving perfectly to prose that no longer says what they cited.
    (
        "spec: every changed heading has been read",
        ROOT / "escapewheel_poc_docs_v0.2",
        [sys.executable, "headings.py", "--check"],
    ),
    # Before the rendering, since a part's column tables come from the registry: a stale one
    # would otherwise be concatenated into the single file and look authoritative.
    (
        "spec: the column tables come from the registry",
        ROOT / "escapewheel_poc_docs_v0.2",
        [sys.executable, "columns.py", "--check"],
    ),
    (
        "spec: the single-file rendering is current",
        ROOT / "escapewheel_poc_docs_v0.2",
        [sys.executable, "combine.py", "--check"],
    ),
    (
        "prototype: write packets",
        ROOT / "prototype/registry-codegen",
        ["uv", "run", "--project", str(TOOLS), "python", "fixture.py"],
    ),
    (
        "prototype: conforming packet is clean",
        ROOT / "prototype/registry-codegen",
        [
            "uv",
            "run",
            "--project",
            str(TOOLS),
            "python",
            "validate.py",
            "packets/valid",
        ],
    ),
    (
        "corpus: write every packet",
        ROOT / "fixtures",
        ["uv", "run", "--project", str(TOOLS), "python", "build.py"],
    ),
    (
        "corpus: every packet behaves as specified",
        ROOT / "fixtures",
        ["uv", "run", "--project", str(TOOLS), "python", "corpus.py"],
    ),
]

#: Run after the generators, never before: a suite passing against stale generated input says
#: nothing. Skipped by --quick, since they are most of the runtime.
SUITES = (
    "escapewheel-reader",
    "escapewheel-validator",
    "escapewheel-writer",
    "escapewheel-aind",
)

#: Directories whose tracked content must be unchanged once the generators have run. Only the
#: ones holding generated output; an unrelated edit elsewhere is not this tool's business.
GENERATED = (
    "registry",
    "prototype",
    "fixtures",
    "escapewheel_poc_docs_v0.2",
    "STATUS.md",
    "TODO.md",
    "CONTRIBUTING.md",
)


def run(cwd: Path, argv: list[str], timeout: float | None) -> tuple[bool, str]:
    """Run one stage, returning whether it passed and its last line of output.

    `TMPDIR` is dropped. The project points scratch at `/mnt/Data` to keep large temporary files
    out of a tmpfs the memory cap cannot hold, and that mount forces root ownership, which pytest
    refuses to write a basetemp into. A caller who has exported it for a build should not have
    the suites fail for it.
    """
    env = {k: v for k, v in os.environ.items() if k != "TMPDIR"}
    try:
        done = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or exc.stderr or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        tail = output.strip().splitlines()
        detail = f"; last output: {tail[-1][:80]}" if tail else ""
        return False, f"timed out after {timeout:g}s{detail}"
    tail = (done.stdout or done.stderr).strip().splitlines()
    return done.returncode == 0, tail[-1] if tail else ""


def candidate_state(where: str) -> dict[str, tuple[int, str]]:
    """Return the content state of every Git-visible change under ``where``.

    Only paths already different from ``HEAD`` need hashing. A generator changing a formerly clean
    path adds it to the set; changing an intentional candidate diff changes its hash; and restoring
    a dirty path removes it. Untracked, non-ignored files are included so a newly generated artifact
    cannot escape merely because it has not been added yet.
    """
    changed = subprocess.run(
        ["git", "diff", "--no-renames", "--name-only", "-z", "HEAD", "--", where],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z", "--", where],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")
    paths = sorted({name.decode() for name in changed + untracked if name})
    state = {}
    for name in paths:
        path = ROOT / name
        if path.is_symlink():
            payload = os.readlink(path).encode()
            mode = path.lstat().st_mode
        elif path.is_file():
            with path.open("rb") as stream:
                payload = hashlib.file_digest(stream, "sha256").digest()
            mode = path.stat().st_mode
        else:
            payload = b"<deleted>"
            mode = 0
        state[name] = (mode & 0o777, hashlib.sha256(payload).hexdigest())
    return state


def state_changes(
    before: dict[str, tuple[int, str]], after: dict[str, tuple[int, str]]
) -> list[str]:
    """Return paths whose candidate state changed between two snapshots."""
    return sorted(
        name
        for name in before.keys() | after.keys()
        if before.get(name) != after.get(name)
    )


def main() -> int:
    """Run every stage in order, reporting each, and return non-zero on any failure."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--quick", action="store_true", help="skip the test suites")
    parser.add_argument(
        "--stage-timeout",
        type=float,
        default=300,
        help="maximum seconds for one stage; 0 disables the timeout (default: 300)",
    )
    args = parser.parse_args()
    if args.stage_timeout < 0:
        parser.error("--stage-timeout cannot be negative")
    timeout = args.stage_timeout or None

    stages = list(STAGES)
    if not args.quick:
        stages += [
            (f"{p}: tests", ROOT / p, ["uv", "run", "pytest", "-q"]) for p in SUITES
        ]

    baseline = {where: candidate_state(where) for where in GENERATED}
    failed = []
    for name, cwd, argv in stages:
        print(f"run  {name}", flush=True)
        clock = time.perf_counter()
        passed, tail = run(cwd, argv, timeout)
        print(
            f"{'ok  ' if passed else 'FAIL'} {name:46s} "
            f"{time.perf_counter() - clock:5.1f}s  {tail[:80]}",
            flush=True,
        )
        if not passed:
            failed.append(name)

    # The one thing no stage above can report: whether generation changed the candidate. Comparing
    # snapshots admits intentional pre-commit diffs while still catching stale or hand-edited output.
    for where in GENERATED:
        changed = state_changes(baseline[where], candidate_state(where))
        if changed:
            failed.append(f"{where}: generation changed the candidate state")
            print(f"FAIL {where}: generation changed {len(changed)} candidate path(s)")
            for name in changed[:10]:
                print(f"       {name}")
        else:
            print(f"ok   {where}: generation preserved the candidate state")

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
