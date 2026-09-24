"""Every citation resolves to a section that exists, and every part is numbered so one can.

A citation is the load-bearing part of a revision: an implementer follows it to the rule. Nothing
checked them, and a wrong one is invisible to every other tool -- `ledger.py` sees that a clause
has a disposition, and a grep for the revision sees a document that exists. Four were found by hand
in one session: Part 02 §10.3 cited twice for a waiver that is §10.1's, R30 §3.2 credited with a
five-column layout it states in seven, Part 07 cited for an Iceberg deferral that is Part 00 §7.3's, and
six references to a draft's §5 left pointing at Consequence after it was restructured.

Three forms are resolved:

    R92 §2.2        against revisions/accepted/R92-*.md
    Part 03 §5.4       against escapewheel_poc_docs_v0.2/03_*.md
    §3.1            against the citing document itself

What fails the build is a revision-to-revision citation that does not resolve, anywhere, and a
part citation that does not resolve in an active **proposal or draft**. Those are the live inputs to
the next specification change, so a broken citation there can become a broken clause in the spec;
an accepted revision is history, and the early ones cite the frozen v0.1 numbering, which exists as
headings in neither compiled spec. Those are counted and shown, not failed.

An unprefixed `§N` that matches no local heading is reported and does not fail: it is usually a
reference whose antecedent is the previous clause ("R86 ... its §1.1"), which reads correctly and
resolves to nothing mechanically. Worth seeing, since the same shape is how a reference to another
document's §7.3 gets read as this document's §7.

Every other working-tree document and source file is checked too, not only the revisions. The parts are
among them: they carry **428 citations** of each other and of the revisions that set their rules,
which were read for numbering alone until this included them, and one named a section of a
revision that has never had one. A broken part citation there is an error, as in a draft, because
the parts are the statement of record.

Every working-tree Python file is checked too, not only the revisions. The current citation rule
sends a comment to the owner that states its rule, so a citation in source is load-bearing -- and until
this scanned them, five were broken: four naming section 56 of Part 00 and section 92 of Part 01,
both v0.1 *line* numbers carried into section form, and one naming a section R70 never had. None
resolved and nothing reported them. A part citation that does not resolve in a tracked file is an
error, as in a draft: the source is live.

Those are spelled out in prose rather than written as citations, because this file is one of the
files it reads.

A part named by its number alone is an error in a part, a revision or a draft, as
`revisions/CONTRIBUTING.md#ew-citation-context` requires and no other check can see: both spellings resolve to the same section. A source file is
read for whether its citations resolve and never for how they are spelled, since a specification
does not impose a comment style on code it does not own.

The parts are also checked for ascending, unique numbering. `headings` returns a set, which is
what hid Part 05 carrying two sections numbered 11 through five accepted revisions -- a duplicate
vanishes into a set and the citation still resolves. Two sections with one number fail the build and
sections that do not ascend are reported.

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
PARTS = HERE.parent / "escapewheel_poc_docs_v0.2"

#: `## 3.` and `### 3.1 ` alike; the trailing dot is optional and the numbering may nest.
HEADING = re.compile(r"^#{1,4} (\d+(?:\.\d+)*)\.?(?:\s|$)", re.MULTILINE)
#: A revision's own number, from its filename.
NUMBER = re.compile(r"^R(\d+)-")
#: `R92 §2.2`, `R92 §2`. The section may end a sentence, so the trailing dot is trimmed.
REVISION = re.compile(r"\bR(\d+) §(\d+(?:\.\d+)*)")
#: `Part 03 §5.4` and the bare `03` §5.4 it replaced, both resolved. Two digits, not `0` and a
#: digit: R93 added Part 10, and a
#: pattern written before it read every Part 10 §x as an unprefixed local reference, which is the
#: bucket that does not fail the build.
PART = re.compile(r"(?:`(\d\d)`|Part (\d\d)) §(\d+(?:\.\d+)*)")
#: Any §, so the ones the two above did not claim can be treated as local.
ANY = re.compile(r"§(\d+(?:\.\d+)*)")
#: A part named by its number alone, which the current citation-context rule forbids in prose. Every
#: backticked two-digit string in those documents is a part, so nothing yet needs excusing.
NUMBERED = re.compile(r"`(\d\d)`")
MARKDOWN_ANCHOR = re.compile(r"\[[^\]]+\]\(([^)\s#]+)#(ew-[a-z0-9-]+)\)")
SOURCE_ANCHOR = re.compile(r"`([^`#]+\.md)#(ew-[a-z0-9-]+)`")
LINKED_PART = re.compile(
    r"\[Part (\d\d) §(\d+(?:\.\d+)*)\]\(([^)\s#]+)#(ew-[a-z0-9-]+)\)"
)

#: Sites where a backticked two-digit number is not a part, or is a specimen of the spelling
#: the former bare-part spelling replaced, each with why. Matched as a substring of the line, and checked to still
#: match something, so an entry cannot outlive the text it excuses.
NOT_A_PART: tuple[tuple[str, str, str], ...] = (
    (
        "R113",
        "at 340**",
        "the revision that chose the spelling, quoting the one it replaced",
    ),
    (
        "R113",
        "in two, both accepted on",
        "the same, showing which of two revisions wrote which",
    ),
    (
        "R113",
        "one sentence, two backticked tokens",
        "the exhibit: a registry field and a part under one markup",
    ),
    ("R113", "becomes", "the possessive form the sweep had to rewrite by hand"),
    (
        "R113",
        "name a part and a stage rather than a section",
        "a shape that takes more than inserting the word",
    ),
)


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
    repeated = sorted(
        {n for n in found if found.count(n) > 1}, key=lambda n: keys[found.index(n)]
    )
    descending = [
        (found[i], found[i + 1]) for i in range(len(keys) - 1) if keys[i + 1] <= keys[i]
    ]
    return repeated, descending


def document(number: str) -> Path | None:
    """The accepted revision with this number, if one exists."""
    found = sorted(ACCEPTED.glob(f"R{number}-*.md"))
    return found[0] if found else None


def part(number: str) -> Path | None:
    """The v0.2 part with this number."""
    found = sorted(PARTS.glob(f"{number}_*.md"))
    return found[0] if found else None


def numbered(path: Path, text: str) -> tuple[list[str], set[str]]:
    """Each part this document names by its number alone, and which exemptions that used.

    The current citation rule binds a part and a revision and nothing else, so source is read
    for whether its citations resolve and never for how they are spelled.
    """
    found, used = [], set()
    for number, line in (
        (m, text[: m.start()].count("\n") + 1) for m in NUMBERED.finditer(text)
    ):
        whole = text.splitlines()[line - 1]
        excuse = next(
            (
                reason
                for site, marker, reason in NOT_A_PART
                if path.name.startswith(site) and marker in whole
            ),
            None,
        )
        if excuse is not None:
            used.add(excuse)
            continue
        found.append(
            f"`{number.group(1)}` on line {line} — a part is named as Part {number.group(1)}"
        )
    return found, used


def anchor_heading(text: str, anchor: str) -> str | None:
    """Return the numbered heading immediately following a canonical anchor."""
    pending = False
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            pending = False
            continue
        if fenced:
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
            if not target.is_file() or anchor not in canonical_anchors(
                target.read_text()
            ):
                errors.append(f"source anchor {relative}#{anchor} does not resolve")
    for part_number, section, relative, anchor in LINKED_PART.findall(text):
        target = resolved.get((relative, anchor))
        if target is None:
            continue
        anchor_section = anchor_heading(target.read_text(), anchor)
        if (
            target.parent != PARTS
            or target.name[:2] != part_number
            or anchor_section != section
        ):
            errors.append(
                f"linked Part {part_number} §{section} disagrees with #{anchor}'s current heading"
            )
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
            errors.append(
                f"R{match.group(1)} §{match.group(2)} — no such accepted revision"
            )
        elif match.group(2) not in headings(target.read_text()):
            errors.append(
                f"R{match.group(1)} §{match.group(2)} — {target.name} has no §{match.group(2)}"
            )
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
            loose.append(
                f"§{match.group(1)} — unprefixed, and this document has no such section"
            )
    # An accepted record is immutable history. Its current-owner links are interpreted from its
    # baseline rather than made a gate on the working tree.
    if path.parent != ACCEPTED:
        errors += anchored(path, text)
    return errors, parts, sorted(set(loose))


#: Read for citations but not for spelling or numbering: the frozen v0.1 specification, which is
#: never edited, and the rendering generated from the v0.2 parts.
SKIPPED = ("nwb_lake_poc_docs/",)

CURRENT_CONTRACT = (
    PARTS / "README.md",
    *sorted(PARTS.glob("[0-9][0-9]_*.md")),
    HERE.parent / "registry/logical_schemas.json",
    HERE.parent / "registry/registry.schema.json",
    HERE.parent / "registry/manifest.schema.json",
    HERE.parent / "registry/sources.schema.json",
    HERE.parent / "registry/rules.json",
    *sorted((HERE.parent / "registry/extensions").glob("*.json")),
    PARTS / "Escapewheel_POC_v0.2_Implementation_Spec.md",
    HERE.parent / "registry/tables.md",
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
    stale_html = HERE.parent / "registry/tables.html"
    if stale_html.exists():
        defects.append("registry/tables.html is present")
    return defects


def elsewhere() -> list[Path]:
    """Every other working-tree document and source file a citation has to resolve in.

    A citation is load-bearing wherever it is written. Reading the revisions and the Python alone
    left the developer documentation unchecked, and seven citations in it resolved to nothing --
    two naming line numbers of the frozen v0.1 as though they were sections, and one naming a
    section of Part 09 that part has never carried. Spelled in prose rather than as citations,
    since this file is one of the files it reads.
    """
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=HERE.parent,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    found = []
    for name in listed:
        path = HERE.parent / name
        if name.startswith(SKIPPED) or "Implementation_Spec" in name:
            continue
        if path.suffix not in {".py", ".md"} or not path.is_file():
            continue
        # The revisions and the drafts are read in their own pass.
        if name.startswith(
            ("revisions/accepted/", "revisions/drafts/", "revisions/proposals/")
        ):
            continue
        found.append(path)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--quiet", action="store_true", help="errors only")
    args = ap.parse_args()

    paths = sorted(
        ACCEPTED.glob("R[0-9]*.md"), key=lambda p: int(NUMBER.match(p.name).group(1))
    )
    paths += sorted((HERE / "proposals").glob("[!.]*.md"))
    paths += sorted((HERE / "drafts").glob("[!.]*.md"))
    # An editor's lock file is a symlink to a target that never existed -- Emacs writes
    # `.#name.md -> user@host:pid`. Following one raises, so a full `verify.py` would fail for as
    # long as any tracked document is open. `is_file()` is false for a dangling link and true for
    # a real one, so this skips the lock and nothing else.
    paths = [p for p in paths if p.is_file()]
    code = elsewhere()
    broken, historical = 0, 0
    excused: set[str] = set()

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
    for target in sorted(PARTS.glob("[0-9][0-9]_*.md")):
        repeated, descending = numbering(target.read_text())
        for number in repeated:
            print(f"  BROKEN  {target.name}: two sections numbered {number}")
            broken += 1
        if not args.quiet:
            for before, after in descending:
                if before != after:
                    print(f"  order   {target.name}: §{after} follows §{before}")

    for path in paths + code:
        # Proposals and drafts feed the next change and a part is the statement of record, so a
        # broken part citation in any of them is an error rather than history. The 428 citations
        # the parts carry were read for numbering alone until this included them, and one named a
        # section of R55 that revision has never had.
        live = (
            path.parent.name in {"proposals", "drafts"}
            or path.suffix == ".py"
            or path.parent == PARTS
        )
        errors, parts, loose = check(path)
        # The current citation rule binds prose spelling; a source file is read only for resolution.
        if path.suffix == ".md":
            spelled, fired = numbered(path, path.read_text())
            errors += spelled
            excused |= fired
        if live:
            errors += parts
        else:
            historical += len(parts)
        broken += len(errors)
        shown = path.relative_to(HERE.parent) if path.suffix == ".py" else path.name
        for line in errors:
            print(f"  BROKEN  {shown}: {line}")
        if not args.quiet:
            for line in parts if not live else []:
                print(f"  v0.1    {shown}: {line}")
            for line in loose:
                print(f"  loose   {shown}: {line}")
    # An exemption that matches nothing is as wrong as a missing one: it excuses text that has
    # gone, and the next reader takes it for a live case.
    for site, _, reason in NOT_A_PART:
        if reason not in excused:
            print(f"  STALE   {site}'s exemption for {reason!r} matches nothing")
            broken += 1

    tail = f", {historical} citing the frozen v0.1 numbering" if historical else ""
    print(
        f"{len(paths)} revision documents and {len(code)} other working-tree files, "
        f"{broken} unresolved citation(s){tail}"
    )
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
