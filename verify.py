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
    python verify.py --heartbeat 30      # report the active stage every 30 seconds
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import signal
import subprocess
import sys
import tempfile
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
        "spec: unit identity declarations agree",
        ROOT / "conformance/unit-identity",
        [sys.executable, "probe.py"],
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
    (
        "spec: framework declarations agree",
        ROOT / "escapewheel_poc_docs_v0.2",
        [sys.executable, "framework.py"],
    ),
    (
        "spec: framework rejects conflicting projections",
        ROOT / "conformance/specification-framework",
        [sys.executable, "probe.py"],
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


def _text(output: str | bytes | None) -> str:
    """Return subprocess output as text, including timeout output documented as bytes."""
    if output is None:
        return ""
    return output.decode(errors="replace") if isinstance(output, bytes) else output


def _last_output(output: str) -> str:
    """Return the last visible output fragment, including one without a newline."""
    lines = output.strip().splitlines()
    return lines[-1] if lines else "no output yet"


def _failure_log(name: str, output: str) -> Path:
    """Preserve complete output for a failed stage outside the candidate tree."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "stage"
    descriptor, filename = tempfile.mkstemp(prefix=f"escapewheel-verify-{slug}-", suffix=".log")
    with os.fdopen(descriptor, "w") as stream:
        stream.write(output)
    return Path(filename)


def _stop(process: subprocess.Popen[str]) -> str:
    """Stop a timed-out stage and every child it started, then return all output."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        stdout, _ = process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, _ = process.communicate()
    return _text(stdout)


def run(
    name: str,
    cwd: Path,
    argv: list[str],
    timeout: float | None,
    heartbeat: float | None,
) -> tuple[bool, str]:
    """Run one stage, reporting progress and preserving complete failure output.

    `TMPDIR` is dropped. The project points scratch at `/mnt/Data` to keep large temporary files
    out of a tmpfs the memory cap cannot hold, and that mount forces root ownership, which pytest
    refuses to write a basetemp into. A caller who has exported it for a build should not have
    the suites fail for it.
    """
    env = {k: v for k, v in os.environ.items() if k != "TMPDIR"}
    # Test names are the useful progress unit. Quiet pytest emits anonymous dots, which made a
    # timeout impossible to locate; verbose output remains captured and only its current line is
    # surfaced by the heartbeat.
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        start_new_session=True,
    )
    started = time.monotonic()
    deadline = None if timeout is None else started + timeout
    output = ""
    while True:
        now = time.monotonic()
        remaining = None if deadline is None else max(0.0, deadline - now)
        wait = heartbeat
        if remaining is not None:
            wait = remaining if wait is None else min(wait, remaining)
        try:
            stdout, _ = process.communicate(timeout=wait)
            output = _text(stdout)
            break
        except subprocess.TimeoutExpired as exc:
            output = _text(exc.stdout or exc.stderr)
            elapsed = time.monotonic() - started
            if deadline is not None and time.monotonic() >= deadline:
                output = _stop(process) or output
                log = _failure_log(name, output)
                return False, (
                    f"timed out after {timeout:g}s; last output: {_last_output(output)[:160]}; "
                    f"full log: {log}"
                )
            print(
                f"wait {name:46s} {elapsed:5.1f}s  {_last_output(output)[:160]}",
                flush=True,
            )

    if process.returncode:
        log = _failure_log(name, output)
        return False, f"{_last_output(output)[:160]}; full log: {log}"
    return True, _last_output(output)


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
    parser.add_argument(
        "--heartbeat",
        type=float,
        default=15,
        help="seconds between progress reports; 0 disables them (default: 15)",
    )
    args = parser.parse_args()
    if args.stage_timeout < 0:
        parser.error("--stage-timeout cannot be negative")
    if args.heartbeat < 0:
        parser.error("--heartbeat cannot be negative")
    timeout = args.stage_timeout or None
    heartbeat = args.heartbeat or None

    stages = list(STAGES)
    if not args.quick:
        stages += [
            (f"{p}: tests", ROOT / p, ["uv", "run", "pytest", "-vv"])
            for p in SUITES
        ]

    baseline = {where: candidate_state(where) for where in GENERATED}
    failed = []
    for name, cwd, argv in stages:
        print(f"run  {name}", flush=True)
        clock = time.perf_counter()
        passed, tail = run(name, cwd, argv, timeout, heartbeat)
        detail = tail[:80] if passed else tail
        print(
            f"{'ok  ' if passed else 'FAIL'} {name:46s} "
            f"{time.perf_counter() - clock:5.1f}s  {detail}",
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
