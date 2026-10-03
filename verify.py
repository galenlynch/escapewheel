"""Run every generator and every check in the monorepo.

The chain is reproducible — `spec/tools/build.py` writes the core registry, the rendered
listing and the source guide's counts; `fixtures/build.py` writes the
conformance corpus — but reproducibility nobody runs is a claim rather than a property: the
corpus stopped building at R54, and the registry README's counts were wrong in five places at
once, before anything noticed.

The load-bearing stage is **regenerate, then demand an unchanged candidate tree**. The candidate
may already contain intentional generated changes, so the verifier snapshots their content before
generation and compares it afterward. A change during verification means the candidate was stale
or a generated file had been edited by hand. Comparing to ``HEAD`` instead would make this command
incapable of passing before the very commit it is meant to check.

Usage:

    python verify.py            # every stage; package suites dominate the runtime
    python verify.py --quick    # every generator and check, and no test suite
    python verify.py --stage-timeout 60  # bound each individual stage
    python verify.py --heartbeat 30      # report each active stage every 30 seconds
    python verify.py --jobs 1            # one stage at a time, in the order declared

The stages that write tracked files run first, alone and in the order declared. Every other stage
only reads the tree, so the rest run together, up to `--jobs` at once.

`--quick` runs none of the package suites and not the integration tests, so it says nothing
about a package's behaviour beyond what the corpus and the conformance checks exercise.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import signal
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent

#: The writer's environment runs whatever needs pyarrow and duckdb outside a package, since it
#: depends on the reader and the validator.
WRITER = ROOT / "escapewheel-writer"
#: The specification's tree, whose tools run in the environment it declares and locks.
TREE = ROOT / "spec" / "tools"
EXTENSIONS = ("extensions", "escapewheel-aind/extensions")


@dataclass(frozen=True)
class Stage:
    """One verifier stage, which fails on a non-zero exit."""

    name: str
    cwd: Path
    #: The uv project whose environment runs `command`.
    project: Path
    command: tuple[str, ...]
    #: Whether the stage writes tracked files. One that does runs alone, before any that reads them.
    writes: bool = False

    @property
    def argv(self) -> list[str]:
        """Return the command line that runs `command` in `project`'s environment."""
        return ["uv", "run", "--project", str(self.project), *self.command]


def _python(name: str, cwd: Path, project: Path, *arguments: str) -> Stage:
    """Return a stage running a script or module with `project`'s interpreter."""
    return Stage(name, cwd, project, ("python", *arguments))


def _generator(name: str, cwd: Path, project: Path, *arguments: str) -> Stage:
    """Return a stage whose script writes tracked files."""
    return replace(_python(name, cwd, project, *arguments), writes=True)


STAGES: list[Stage] = [
    _generator("spec: generate", TREE, TREE, "build.py"),
    _generator("extensions: generate", ROOT, TREE, "extensions/registries.py", "build", *EXTENSIONS),
    _generator("root: the documents' counts are current", ROOT, WRITER, "tools/facts.py"),
    _python("revisions: open stages are structurally complete", ROOT, WRITER, "revisions/stages.py"),
    _python("revisions: process tooling tests", ROOT, WRITER, "-m", "unittest", "revisions.test_evidence"),
    _python("root: verifier control-flow tests", ROOT, WRITER, "-m", "unittest", "tools.test_verify"),
    _python("revisions: process semantics tests", ROOT, WRITER, "revisions/test_process.py"),
    _python("revisions: accepted evidence manifests resolve", ROOT, WRITER, "revisions/evidence.py"),
    _python("spec: structural checks", TREE, TREE, "check.py"),
    Stage("spec: checker tests", TREE, TREE, ("pytest", "-q", "-p", "no:cacheprovider", "-n", "8")),
    # CONTRIBUTING.md's rules for the tree: it regenerates and checks itself alone, and its tools
    # import only what it declares and locks.
    _python("spec: the tree regenerates and checks itself alone", ROOT, WRITER, "tools/tree.py"),
    _python("packages: copies from the tree agree", ROOT, WRITER, "tools/copies.py", "--check"),
    _python(
        "extensions: each registry checked where it sits",
        ROOT,
        TREE,
        "extensions/registries.py",
        "check",
        *EXTENSIONS,
    ),
    _python("registries: ledger and rule execution", ROOT, WRITER, "conformance/registries/check.py"),
    _python(
        "registries: history cleanup preserves declarations",
        ROOT / "conformance/history-cleanup",
        WRITER,
        "probe.py",
    ),
    _python(
        "registry: R126 migration and external-domain evidence",
        ROOT / "conformance/registry-contract",
        ROOT / "escapewheel-validator",
        "probe.py",
    ),
    _python(
        "rules: portable language vectors and shipped rules",
        ROOT / "conformance/rule-language",
        WRITER,
        "probe.py",
    ),
    _python("spec: unit identity declarations agree", ROOT / "conformance/unit-identity", WRITER, "probe.py"),
    _python(
        "citations: every live one resolves, and no part number repeats",
        ROOT / "revisions",
        WRITER,
        "check_citations.py",
        "--quiet",
    ),
    # The current-owner rule in `revisions/CONTRIBUTING.md#ew-citation-context`: a citation of a clause
    # that landed in a part resolves perfectly while still sending a reader to the change record, so
    # nothing else can see it.
    _python("citations: a requirement names its part", ROOT / "revisions", WRITER, "repoint.py", "--quiet"),
    _python("citations: every exemption is still needed", ROOT / "revisions", WRITER, "repoint.py", "--exempt"),
    # Every accepted clause has an entry, whose current owner, JSON target or successor resolves.
    _python("spec: every revision clause has a disposition", ROOT / "revisions", WRITER, "ledger.py", "--summary"),
    # The other half of what a citation needs. `check_citations.py` resolves a number and this
    # records what the number is about, so a section that keeps one and changes the other cannot
    # leave its citers resolving perfectly to prose that no longer says what they cited.
    _python("spec: every changed heading has been read", TREE, TREE, "headings.py", "--check"),
    _python("spec: framework declarations agree", TREE, TREE, "framework.py"),
    _python(
        "spec: framework rejects conflicting projections",
        ROOT / "conformance/specification-framework",
        WRITER,
        "probe.py",
    ),
    # Before the rendering, since a part's column tables come from the registry: a stale one
    # would otherwise be concatenated into the single file and look authoritative.
    _python("spec: the column tables come from the registry", TREE, TREE, "columns.py", "--check"),
    # Part 08 shows a packet the writer builds, so its layout and manifest follow the registries.
    _python("spec: Part 08 shows the packet the writer builds", ROOT / "integration", WRITER, "example.py"),
    _python("spec: the single-file rendering is current", TREE, TREE, "combine.py", "--check"),
    _generator("corpus: write every packet", ROOT / "fixtures", WRITER, "build.py"),
    _python("corpus: every packet behaves as specified", ROOT / "fixtures", WRITER, "corpus.py"),
]

#: Run after the generators, never before: a suite passing against stale generated input says
#: nothing. Skipped by --quick, since they are most of the runtime.
#: The last runs the writer, reader and validator against one another; it is not a project of
#: its own, so it runs in the writer's environment, which carries all three.
SUITES: list[Stage] = [
    *(
        Stage(f"{package}: tests", ROOT / package, ROOT / package, ("pytest", "-vv", *workers))
        # A suite of a few seconds runs in one process, since starting workers costs about as much.
        for package, workers in (
            ("escapewheel-reader", ()),
            ("escapewheel-validator", ("-n", "4")),
            ("escapewheel-writer", ("-n", "6")),
            ("escapewheel-aind", ()),
            ("escapewheel-dev", ()),
        )
    ),
    Stage("integration: tests", ROOT / "integration", WRITER, ("pytest", "-vv")),
]

# Full verification needs facilities that some restricted execution environments deny or cannot
# wake. Prove those facilities before doing any of the comparatively expensive generation and
# corpus work, rather than discovering the problem in a package fixture after many minutes.
RUNTIME_CAPABILITY_STAGE = _python("runtime: full-suite capabilities", ROOT, WRITER, "tools/runtime_capabilities.py")

#: Directories whose tracked content must be unchanged once the generators have run. Only the
#: ones holding generated output; an unrelated edit elsewhere is not this tool's business.
GENERATED = (
    "spec",
    "extensions",
    "escapewheel-aind/extensions",
    "fixtures",
    "STATUS.md",
    "TODO.md",
    "CONTRIBUTING.md",
)


_REPORT = threading.Lock()


def _say(line: str = "") -> None:
    """Print one whole line, which stages running together would otherwise interleave."""
    with _REPORT:
        print(line, flush=True)


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
                    f"timed out after {timeout:g}s; last output: {_last_output(output)[:160]}; full log: {log}"
                )
            _say(f"wait {name:46s} {elapsed:5.1f}s  {_last_output(output)[:160]}")

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


def state_changes(before: dict[str, tuple[int, str]], after: dict[str, tuple[int, str]]) -> list[str]:
    """Return paths whose candidate state changed between two snapshots."""
    return sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))


def _reported(stage: Stage, timeout: float | None, heartbeat: float | None) -> bool:
    """Run one stage, printing its name before and its outcome after, and return whether it passed."""
    _say(f"run  {stage.name}")
    clock = time.perf_counter()
    passed, tail = run(stage.name, stage.cwd, stage.argv, timeout, heartbeat)
    detail = tail[:80] if passed else tail
    _say(f"{'ok  ' if passed else 'FAIL'} {stage.name:46s} {time.perf_counter() - clock:5.1f}s  {detail}")
    return passed


def main() -> int:
    """Run every stage, reporting each, and return non-zero on any failure."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--quick",
        action="store_true",
        help="run no package or integration test suite, and skip the runtime preflight they need",
    )
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
    parser.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        help="how many stages that only read the tree run at once (default: one per CPU)",
    )
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if args.stage_timeout < 0:
        parser.error("--stage-timeout cannot be negative")
    if args.heartbeat < 0:
        parser.error("--heartbeat cannot be negative")
    timeout = args.stage_timeout or None
    heartbeat = args.heartbeat or None

    if not args.quick and not _reported(RUNTIME_CAPABILITY_STAGE, timeout, heartbeat):
        print("\nfull verification stopped before generation and package tests")
        print("use --quick for checks that do not require these runtime capabilities")
        return 1

    stages = list(STAGES)
    if not args.quick:
        stages += SUITES

    baseline = {where: candidate_state(where) for where in GENERATED}
    # A stage that reads the tree must see what the generators wrote, so the writers finish first.
    writers = [stage for stage in stages if stage.writes]
    readers = [stage for stage in stages if not stage.writes]
    passed = [_reported(stage, timeout, heartbeat) for stage in writers]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        passed += pool.map(lambda stage: _reported(stage, timeout, heartbeat), readers)
    failed = [stage.name for stage, ok in zip(writers + readers, passed, strict=True) if not ok]

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
