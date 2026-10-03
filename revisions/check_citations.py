"""Every citation in a live document resolves to a section that exists, and every part is numbered so one can.

Three forms are resolved:

    R92 §2.2        against revisions/accepted/R92-*.md
    Part 03 §5.4    against spec/parts/03_*.md
    §3.1            against the citing document itself

A live document is a change document, a numbered part, or any other tracked Markdown or Python
file. An accepted revision, a project review and the frozen v0.1 specification are history: they are
read against the baseline they were written on, never gated on the current tree
(`revisions/CONTRIBUTING.md#ew-citation-context`). The exception is an accepted revision `HEAD` does
not yet hold, whose baseline is the tree it is incorporated into, so it is read like a live document.
An accepted revision from R167 onward also may not cite a document that has not been accepted.

A revision or part citation that does not resolve fails. An unprefixed
`§N` matching no local heading is reported and does not fail, since it usually continues a
reference to another document from the previous clause.

A part named by its number alone fails in a Markdown document, as the citation-context rule
requires; source is read only for whether its citations resolve. The parts are also checked for
unique numbering, which fails the build, and for ascending numbering, which is reported: a
duplicate number makes a citation ambiguous rather than unresolvable.

    python check_citations.py            # report
    python check_citations.py --quiet    # errors only
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    from revisions.process_rules import canonical_anchors
except ModuleNotFoundError:  # Direct execution from revisions/.
    from process_rules import canonical_anchors

HERE = Path(__file__).resolve().parent
ACCEPTED = HERE / "accepted"
CHANGES = HERE / "changes"
SPEC = HERE.parent / "spec"
PARTS = SPEC / "parts"
sys.path.insert(0, str(SPEC / "tools"))

import specdoc

HEADING = specdoc.HEADING
#: `R92 §2.2`, `R92 §2`. The section may end a sentence, so the trailing dot is trimmed.
REVISION = specdoc.REVISION_CITATION
#: `Part 03 §5.4` and the bare `03` §5.4 it replaced, both resolved. Two digits, not `0` and a
#: digit: R93 added Part 10, and a
#: pattern written before it read every Part 10 §x as an unprefixed local reference, which is the
#: bucket that does not fail the build. One space separates the part from the section sign.
PART = specdoc.part_citation(" ")
#: Any §, so the ones the two above did not claim can be treated as local.
ANY = specdoc.SECTION_CITATION
#: A part named by its number alone, which the current citation-context rule forbids in prose. Every
#: backticked two-digit string in those documents is a part, so nothing yet needs excusing.
NUMBERED = re.compile(r"`(\d\d)`")
MARKDOWN_ANCHOR = re.compile(r"\[[^\]]+\]\(([^)\s#]+)#(ew-[a-z0-9-]+)\)")
SOURCE_ANCHOR = re.compile(r"`([^`#]+\.md)#(ew-[a-z0-9-]+)`")
LINKED_PART = re.compile(rf"\[Part (\d\d) §({specdoc.SECTION})\]\(([^)\s#]+)#(ew-[a-z0-9-]+)\)")
#: A path into a directory that holds, or once held, documents not yet accepted.
UNACCEPTED_PATH = re.compile(r"\b(?:changes|proposals|drafts)/[a-z0-9-]+\.md\b")
#: The first accepted revision that may cite no unaccepted document.
SELF_CONTAINED_FROM = 167


def headings(text: str) -> set[str]:
    """Every section number a document declares, at any depth."""
    return set(HEADING.findall(text))


def numbering(text: str) -> tuple[list[str], list[tuple[str, str]]]:
    """A part's repeated section numbers, and each adjacent pair that fails to ascend.

    Compared as tuples of integers, so `1.10` follows `1.9` and a nested section follows its
    parent. Every repeat is also a non-ascending pair; both are returned because the process makes
    the first an error and the second a report.
    """
    found = HEADING.findall(text)
    keys = [tuple(int(part) for part in number.split(".")) for number in found]
    repeated = sorted({n for n in found if found.count(n) > 1}, key=lambda n: keys[found.index(n)])
    descending = [(found[i], found[i + 1]) for i in range(len(keys) - 1) if keys[i + 1] <= keys[i]]
    return repeated, descending


def document(number: str) -> Path | None:
    """The accepted revision with this number, if one exists."""
    found = sorted(ACCEPTED.glob(f"R{number}-*.md"))
    return found[0] if found else None


def part(number: str) -> Path | None:
    """The v0.2 part with this number."""
    return specdoc.part_path(PARTS, number)


def numbered(text: str) -> list[str]:
    """Each part this document names by its number alone."""
    lines = (text[: match.start()].count("\n") + 1 for match in NUMBERED.finditer(text))
    return [
        f"`{match.group(1)}` on line {line} — a part is named as Part {match.group(1)}"
        for match, line in zip(NUMBERED.finditer(text), lines, strict=True)
    ]


def anchor_heading(text: str, anchor: str) -> str | None:
    """Return the numbered heading immediately following a canonical anchor."""
    pending = False
    for _, line in specdoc.outside_fences(text):
        if line is None:
            pending = False
            continue
        if anchor in canonical_anchors(line):
            pending = True
            continue
        if pending and line.strip():
            match = HEADING.match(line)
            return match.group(1) if match else None
    return None


def anchored(path: Path, text: str) -> list[str]:
    """Return unresolved stable-anchor links and linked part-number disagreements."""
    errors = []
    root = HERE.parent
    resolved: dict[tuple[str, str], Path] = {}
    for match in MARKDOWN_ANCHOR.finditer(text):
        relative, anchor = match.groups()
        target = (path.parent / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f"anchor link {relative}#{anchor} escapes the repository")
            continue
        if not target.is_file() or anchor not in canonical_anchors(target.read_text()):
            errors.append(f"anchor link {relative}#{anchor} does not resolve")
        else:
            resolved[relative, anchor] = target
    if path.suffix == ".py":
        for relative, anchor in SOURCE_ANCHOR.findall(text):
            target = (root / relative).resolve()
            if not target.is_file() or anchor not in canonical_anchors(target.read_text()):
                errors.append(f"source anchor {relative}#{anchor} does not resolve")
    for part_number, section, relative, anchor in LINKED_PART.findall(text):
        target = resolved.get((relative, anchor))
        if target is None:
            continue
        anchor_section = anchor_heading(target.read_text(), anchor)
        if target.parent != PARTS or target.name[:2] != part_number or anchor_section != section:
            errors.append(f"linked Part {part_number} §{section} disagrees with #{anchor}'s current heading")
    return errors


def check(path: Path) -> tuple[list[str], list[str], list[str]]:
    """Return this document's unresolved revision citations, part citations and local references.

    A source file declares no sections, so an unprefixed `§N` in one resolves to its enclosing
    prose rather than to a heading and is not reported.
    """
    text = path.read_text()
    own = headings(text) if path.suffix == ".md" else None
    errors, parts, loose = [], [], []
    claimed: set[tuple[int, int]] = set()

    for match in REVISION.finditer(text):
        claimed.add(match.span())
        target = document(match.group(1))
        if target is None:
            errors.append(f"R{match.group(1)} §{match.group(2)} — no such accepted revision")
        elif match.group(2) not in headings(target.read_text()):
            errors.append(f"R{match.group(1)} §{match.group(2)} — {target.name} has no §{match.group(2)}")
    for match in PART.finditer(text):
        claimed.add(match.span())
        name, section = match.group(1) or match.group(2), match.group(3)
        target = part(name)
        if target is None:
            parts.append(f"`{name}` §{section} — no such part")
        elif section not in headings(target.read_text()):
            parts.append(f"`{name}` §{section} — {target.name} has no §{section}")

    spans = [(a, b) for a, b in claimed]
    for match in ANY.finditer(text) if own is not None else ():
        if any(a <= match.start() < b for a, b in spans):
            continue
        if match.group(1) not in own:
            loose.append(f"§{match.group(1)} — unprefixed, and this document has no such section")
    errors += anchored(path, text)
    return errors, parts, sorted(set(loose))


#: History, read against the baseline it was written on, and the rendering generated from the parts.
HISTORICAL = ("revisions/baseline-v0.1/", "revisions/accepted/", "revisions/reviews/")

CURRENT_CONTRACT = (
    SPEC / "README.md",
    *specdoc.part_paths(PARTS),
    SPEC / "artifacts/logical_schemas.json",
    SPEC / "artifacts/registry.schema.json",
    SPEC / "artifacts/manifest.schema.json",
    SPEC / "artifacts/sources.schema.json",
    *sorted((HERE.parent / "extensions").glob("*.json")),
    *sorted((HERE.parent / "escapewheel-aind/extensions").glob("*.json")),
    SPEC / "informative/Escapewheel_POC_v0.2_Implementation_Spec.md",
    SPEC / "informative/tables.md",
)


def current_contract_history_refs() -> list[str]:
    """Return revision-record references in current owners and generated projections."""
    defects = []
    for path in CURRENT_CONTRACT:
        if not path.is_file():
            defects.append(f"{path.relative_to(HERE.parent)} is absent")
            continue
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"\bR\d+\b", line):
                defects.append(f"{path.relative_to(HERE.parent)}:{line_number}")
    stale_html = SPEC / "informative/tables.html"
    if stale_html.exists():
        defects.append("spec/informative/tables.html is present")
    return defects


def committed(path: Path) -> bool:
    """Whether `HEAD` holds this file, which makes an accepted record history."""
    target = f"HEAD:{path.relative_to(HERE.parent).as_posix()}"
    return subprocess.run(["git", "cat-file", "-e", target], cwd=HERE.parent, capture_output=True).returncode == 0


def incoming() -> list[Path]:
    """Accepted records the working tree adds, which are checked as live until committed."""
    return [p for p in sorted(ACCEPTED.glob("R[0-9]*.md")) if p.is_file() and not committed(p)]


def unaccepted_citations(path: Path) -> list[str]:
    """Each citation, in an accepted record from `SELF_CONTAINED_FROM` on, of an unaccepted document."""
    number = re.match(r"R(\d+)-", path.name)
    if path.parent != ACCEPTED or number is None or int(number.group(1)) < SELF_CONTAINED_FROM:
        return []
    text = path.read_text()
    names = {p.name for p in CHANGES.glob("[!.]*.md") if p.name != "README.md"}
    found = [match.group() for match in UNACCEPTED_PATH.finditer(text)]
    found += [name for name in sorted(names) if f"`{name}`" in text]
    return [f"cites `{name}`, which has not been accepted" for name in found]


def elsewhere() -> list[Path]:
    """Every live working-tree document and source file other than the change documents."""
    listed = specdoc.tracked_files(HERE.parent, whole_names=False)
    found = []
    for name in listed:
        path = HERE.parent / name
        if name.startswith(HISTORICAL) or "Implementation_Spec" in name:
            continue
        if path.suffix not in {".py", ".md"} or not path.is_file():
            continue
        # The change documents are read in their own pass.
        if name.startswith("revisions/changes/"):
            continue
        found.append(path)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--quiet", action="store_true", help="errors only")
    args = ap.parse_args()

    paths = sorted(p for p in CHANGES.glob("[!.]*.md") if p.name != "README.md")
    # An editor's lock file is a symlink to a target that never existed -- Emacs writes
    # `.#name.md -> user@host:pid`. Following one raises, so a full `verify.py` would fail for as
    # long as any tracked document is open. `is_file()` is false for a dangling link and true for
    # a real one, so this skips the lock and nothing else.
    paths = [p for p in paths if p.is_file()]
    code = elsewhere()
    records = incoming()
    broken = 0

    history_defects = current_contract_history_refs()
    history_label = "current contract artifacts contain no revision references"
    if history_defects:
        for defect in history_defects[:20]:
            print(f"  BROKEN  {history_label}: {defect}")
        broken += len(history_defects)
    elif not args.quiet:
        print(f"  ok      {history_label}")

    # Unique ascending numbering is checked before any citation: a duplicate number makes a citation
    # ambiguous rather than unresolvable, so nothing downstream can see it.
    for target in specdoc.part_paths(PARTS):
        repeated, descending = numbering(target.read_text())
        for number in repeated:
            print(f"  BROKEN  {target.name}: two sections numbered {number}")
            broken += 1
        if not args.quiet:
            for before, after in descending:
                if before != after:
                    print(f"  order   {target.name}: §{after} follows §{before}")

    for path in paths + records + code:
        errors, parts, loose = check(path)
        errors += parts
        errors += unaccepted_citations(path)
        # The current citation rule binds prose spelling; a source file is read only for resolution.
        if path.suffix == ".md":
            errors += numbered(path.read_text())
        broken += len(errors)
        shown = path.relative_to(HERE.parent) if path.suffix == ".py" else path.name
        for line in errors:
            print(f"  BROKEN  {shown}: {line}")
        if not args.quiet:
            for line in loose:
                print(f"  loose   {shown}: {line}")
    print(
        f"{len(paths)} change documents, {len(records)} uncommitted accepted records and {len(code)} other "
        f"live files, {broken} unresolved citation(s)"
    )
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
