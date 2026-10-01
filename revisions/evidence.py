"""Validate accepted-revision change and evidence manifests.

Every accepted revision using the current `Decision clauses` metadata has one JSON manifest under
`revisions/evidence/`. The manifest maps each clause to its normative owners, generated projections,
conformance evidence, implementation surfaces, and human documentation. It records evidence; it
does not make tests or implementations authoritative.

Only the manifest of a revision being accepted, whose record `HEAD` does not yet hold, is resolved
against the working tree. Once committed, a manifest is part of an immutable accepted record, which
need not resolve against the current specification (`revisions/CONTRIBUTING.md#ew-citation-context`),
so it is checked for shape and clause coverage alone.
"""

from __future__ import annotations

import ast
import functools
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from revisions.process_rules import canonical_anchors
except ModuleNotFoundError:  # Direct execution from revisions/.
    from process_rules import canonical_anchors

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "revisions"
ACCEPTED = HERE / "accepted"
MANIFESTS = HERE / "evidence"
DECLARED = re.compile(r"^\|\s*\*\*Decision clauses\*\*\s*\|\s*(.*?)\s*\|$", re.MULTILINE)
CLAUSE = re.compile(r"§(\d+(?:\.\d+)*)")
REVISION = re.compile(r"R(\d+)")
SHA = re.compile(r"[0-9a-f]{40}")
SURFACES = ("projections", "implementations", "documentation")


def resolve_path(value: object) -> tuple[Path | None, str | None]:
    """Resolve a repository-relative path without permitting an escape from the repository."""
    if not isinstance(value, str) or not value:
        return None, "path is not a nonempty string"
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        return None, f"{value!r} escapes the repository"
    if not path.exists():
        return None, f"{value!r} does not exist"
    return path, None


def json_pointer(document: object, value: object) -> str | None:
    """Return a defect if an RFC 6901 pointer does not resolve."""
    if not isinstance(value, str) or not value.startswith("/"):
        return "JSON owner needs a nonempty pointer beginning with `/`"
    current = document
    try:
        for raw in value[1:].split("/"):
            token = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict):
                current = current[token]
            elif isinstance(current, list) and token.isdigit():
                current = current[int(token)]
            else:
                return f"pointer {value!r} follows a scalar at {token!r}"
    except (KeyError, IndexError):
        return f"pointer {value!r} does not resolve"
    return None


def owner_defects(owner: object) -> list[str]:
    """Validate one normative owner target."""
    if not isinstance(owner, dict):
        return [f"owner {owner!r} is not an object"]
    path, defect = resolve_path(owner.get("path"))
    if defect:
        return [defect]
    assert path is not None
    if path.suffix == ".md":
        anchor = owner.get("anchor")
        if not isinstance(anchor, str) or anchor not in canonical_anchors(path.read_text()):
            return [f"{owner.get('path')} has no canonical #{anchor}"]
        if set(owner) != {"path", "anchor"}:
            return [f"Markdown owner has fields other than path and anchor: {sorted(owner)}"]
        return []
    if path.suffix == ".json":
        if set(owner) != {"path", "pointer"}:
            return [f"JSON owner has fields other than path and pointer: {sorted(owner)}"]
        try:
            document = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            return [f"{owner.get('path')} is not JSON: {exc}"]
        defect = json_pointer(document, owner.get("pointer"))
        return [defect] if defect else []
    return [f"owner {owner.get('path')!r} is neither Markdown nor JSON"]


def surface_defects(name: str, value: object, resolve: bool = True) -> list[str]:
    """Validate an affected-path list or a reason the surface is unchanged."""
    if not isinstance(value, dict) or set(value) - {"paths", "unchanged"}:
        return [f"{name} must contain only `paths` or `unchanged`"]
    paths, unchanged = value.get("paths"), value.get("unchanged")
    has_paths = isinstance(paths, list) and bool(paths)
    has_reason = isinstance(unchanged, str) and bool(unchanged.strip())
    if has_paths == has_reason:
        return [f"{name} must name nonempty paths or one unchanged reason, but not both"]
    defects = []
    if has_paths and resolve:
        for item in paths:
            path, defect = resolve_path(item)
            if defect:
                defects.append(defect)
            elif path is not None and not path.is_file():
                defects.append(f"{item!r} is not an exact file path")
    return defects


def fixture_expectations() -> dict[str, tuple[str, str] | None]:
    """Read the corpus's literal EXPECTED map without importing the implementation."""
    tree = ast.parse((ROOT / "fixtures/corpus.py").read_text())
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "EXPECTED"
            and node.value is not None
        ):
            return ast.literal_eval(node.value)
    raise ValueError("fixtures/corpus.py has no literal EXPECTED map")


@functools.cache
def verifier_checks() -> dict[str, Path]:
    """Return verifier stage names mapped to the Python check each stage collects."""
    spec = importlib.util.spec_from_file_location("escapewheel_verify", ROOT / "verify.py")
    if spec is None or spec.loader is None:
        raise ValueError("verify.py cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks = {}
    for name, cwd, argv in module.STAGES:
        script = next((argument for argument in argv if str(argument).endswith(".py")), None)
        if script is not None:
            checks[name] = (cwd / script).resolve()
    return checks


def evidence_defects(value: object, collections: list[tuple[str, str]]) -> list[str]:  # noqa: C901
    """Validate conformance evidence and queue pytest node IDs for collection."""
    if not isinstance(value, dict) or set(value) - {"evidence", "not_applicable"}:
        return ["conformance must contain only `evidence` or `not_applicable`"]
    rows, reason = value.get("evidence"), value.get("not_applicable")
    has_rows = isinstance(rows, list) and bool(rows)
    has_reason = isinstance(reason, str) and bool(reason.strip())
    if has_rows == has_reason:
        return ["conformance must name evidence or one not-applicable reason, but not both"]
    if not has_rows:
        return []
    defects = []
    expected = fixture_expectations()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("kind"), str):
            defects.append(f"evidence {row!r} has no kind")
            continue
        kind = row["kind"]
        if kind == "pytest":
            if set(row) != {"kind", "project", "nodeid"}:
                defects.append("pytest evidence needs exactly kind, project, and nodeid")
                continue
            project, nodeid = row.get("project"), row.get("nodeid")
            project_path, project_defect = resolve_path(project)
            test_path = str(nodeid).split("::", 1)[0]
            test, test_defect = resolve_path(f"{project}/{test_path}")
            if project_defect or project_path is None or not (project_path / "pyproject.toml").is_file():
                defects.append(project_defect or f"{project!r} is not a Python project")
            elif test_defect or test is None or "::" not in str(nodeid):
                defects.append(test_defect or f"{nodeid!r} is not a pytest node ID")
            else:
                try:
                    test.relative_to(project_path)
                except ValueError:
                    defects.append(f"pytest node {nodeid!r} is outside project {project!r}")
                else:
                    collections.append((str(project), str(nodeid)))
        elif kind == "fixture":
            if set(row) != {"kind", "packet", "finding"}:
                defects.append("fixture evidence needs exactly kind, packet, and finding")
                continue
            packet, finding = row.get("packet"), row.get("finding")
            if packet not in expected:
                defects.append(f"fixture packet {packet!r} is not collected by corpus.py")
            elif not (ROOT / "fixtures" / "packets" / str(packet)).is_dir():
                defects.append(f"fixture packet {packet!r} has no packet directory")
            elif expected[packet] is None or expected[packet][1] != finding:
                defects.append(f"fixture {packet!r} does not expect finding {finding!r}")
        elif kind == "check":
            if set(row) != {"kind", "stage", "id"}:
                defects.append("check evidence needs exactly kind, stage, and id")
                continue
            stage = row.get("stage")
            identifier = row.get("id")
            path = verifier_checks().get(stage) if isinstance(stage, str) else None
            if path is None:
                defects.append(f"check stage {stage!r} is not collected by verify.py")
            elif not isinstance(identifier, str) or identifier not in path.read_text():
                defects.append(f"check identifier {identifier!r} is not declared by stage {stage!r}")
        else:
            defects.append(f"unknown evidence kind {kind!r}")
    return defects


def collected(project: str) -> tuple[set[str], str | None]:
    """Return every node ID the package suite collects, or a collection defect."""
    env = dict(os.environ)
    env.setdefault("UV_CACHE_DIR", "/tmp/escapewheel-uv-cache")
    done = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(ROOT / project),
            "pytest",
            "--collect-only",
            "-q",
        ],
        cwd=ROOT / project,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=60,
    )
    if done.returncode:
        tail = (done.stdout or done.stderr).strip().splitlines()
        return set(), f"{project} test collection failed" + (f": {tail[-1]}" if tail else "")
    return {line.strip() for line in done.stdout.splitlines() if "::" in line}, None


def accepted() -> dict[str, tuple[Path, set[str]]]:
    """Return accepted revisions using explicit Decision clauses."""
    found = {}
    for path in ACCEPTED.glob("R[0-9]*.md"):
        match = REVISION.match(path.name)
        declared = DECLARED.search(path.read_text()[:2000])
        if match and declared:
            revision = f"R{match.group(1)}"
            found[revision] = (
                path,
                {f"{revision} §{s}" for s in CLAUSE.findall(declared.group(1))},
            )
    return found


def committed(record: Path) -> bool:
    """Whether `HEAD` holds this accepted record, making its manifest historical."""
    target = f"HEAD:{record.relative_to(ROOT).as_posix()}"
    return (
        subprocess.run(
            ["git", "cat-file", "-e", target],
            cwd=ROOT,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def manifest_defects(  # noqa: C901
    path: Path,
    revision: str,
    expected: set[str],
    collections: list[tuple[str, str]],
    resolve: bool = True,
) -> list[str]:
    """Validate one manifest against its accepted revision, resolving its targets if `resolve`."""
    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]
    if not isinstance(document, dict):
        return ["top level is not an object"]
    defects = []
    if set(document) != {"version", "revision", "based_on", "clauses"}:
        defects.append(f"top-level fields are {sorted(document)}, not the required four")
    if document.get("version") != 1:
        defects.append("version is not 1")
    if document.get("revision") != revision:
        defects.append(f"revision is {document.get('revision')!r}, expected {revision!r}")
    baseline = document.get("based_on")
    if not isinstance(baseline, str) or not SHA.fullmatch(baseline):
        defects.append("based_on is not a full commit hash")
    else:
        exists = (
            subprocess.run(
                ["git", "cat-file", "-e", f"{baseline}^{{commit}}"],
                cwd=ROOT,
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
        if not exists:
            defects.append(f"based_on commit {baseline} does not exist")
    clauses = document.get("clauses")
    if not isinstance(clauses, dict):
        return defects + ["clauses is not an object"]
    if set(clauses) != expected:
        defects.append(f"clause keys are {sorted(clauses)}, expected {sorted(expected)}")
    for clause, record in clauses.items():
        if not isinstance(record, dict):
            defects.append(f"{clause}: record is not an object")
            continue
        required = {
            "owners",
            "projections",
            "conformance",
            "implementations",
            "documentation",
        }
        if set(record) != required:
            defects.append(f"{clause}: fields are {sorted(record)}, expected {sorted(required)}")
            continue
        owners = record["owners"]
        if not isinstance(owners, list) or not owners:
            defects.append(f"{clause}: owners is not a nonempty list")
        elif resolve:
            defects += [f"{clause}: {item}" for owner in owners for item in owner_defects(owner)]
        for surface in SURFACES:
            defects += [f"{clause}: {item}" for item in surface_defects(surface, record[surface], resolve)]
        if not resolve:
            continue
        defects += [f"{clause}: {item}" for item in evidence_defects(record["conformance"], collections)]
    return defects


def main() -> int:
    """Check manifest coverage, paths, pointers, and evidence collection."""
    revisions = accepted()
    manifests = {path.stem: path for path in MANIFESTS.glob("R*.json")}
    defects = []
    for revision in sorted(set(revisions) - set(manifests), key=lambda value: int(value[1:])):
        defects.append(f"{revision}: accepted revision has no evidence manifest")
    for revision in sorted(set(manifests) - set(revisions), key=lambda value: int(value[1:])):
        defects.append(f"{revision}: manifest has no accepted revision with Decision clauses")
    collections: list[tuple[str, str]] = []
    resolved = 0
    for revision in sorted(set(revisions) & set(manifests), key=lambda value: int(value[1:])):
        path = manifests[revision]
        resolve = not committed(revisions[revision][0])
        resolved += resolve
        for defect in manifest_defects(path, revision, revisions[revision][1], collections, resolve):
            defects.append(f"{path.relative_to(ROOT)}: {defect}")
    requested: dict[str, set[str]] = {}
    for project, nodeid in collections:
        requested.setdefault(project, set()).add(nodeid)
    for project, nodeids in sorted(requested.items()):
        try:
            found, defect = collected(project)
        except subprocess.TimeoutExpired:
            found, defect = set(), f"{project} test collection timed out"
        if defect:
            defects.append(defect)
            continue
        for nodeid in sorted(nodeids - found):
            defects.append(f"{project}/{nodeid} is not collected by the package suite")
    for defect in defects:
        print(f"  {defect}")
    if defects:
        print(f"{len(defects)} revision evidence defect(s)")
        return 1
    print(
        f"{len(manifests)} revision evidence manifest(s) cover every current-format accepted revision; "
        f"{resolved} manifest(s) of uncommitted revisions resolved against the working tree"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
