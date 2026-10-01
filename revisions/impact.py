"""Who cites the specification sections a change touches.

A part's section is the statement of record, so editing one silently invalidates whatever pointed
at it. Part 03 §5.5 carries 15 citations across the writer, the parts and the revisions, and R110
rewrote it without any of them being read. `check_citations.py` answers the other direction — does
this citation resolve — and cannot see that a resolved citation now points at different prose.

    python revisions/impact.py              # what the working tree changes, and who cites it
    python revisions/impact.py HEAD~3       # the same for a commit range
    python revisions/impact.py --section 02:7.1 --section 05:8
    python revisions/impact.py --anchor ew-session-scope

Reports each changed section with every working-tree file that cites it. It says nothing about whether a citer
is stale, which needs reading: what it removes is having to find them first.
"""

from __future__ import annotations

import argparse
import functools
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "spec" / "parts"

#: A heading that opens a numbered section, at any depth.
HEADING = re.compile(r"^#{2,4} (\d+(?:\.\d+)*)\.? +(.+)$")

#: `Part 03 §5.4`, as required by `revisions/CONTRIBUTING.md#ew-citation-context`, and the bare
#: `03` §5.4 it replaced: a citation
#: written before that clause still resolves, so both are read here.
CITATION = re.compile(r"(?:`(\d\d)`|Part (\d\d))\s+§(\d+(?:\.\d+)*)")
ANCHOR = re.compile(r'^<a id="([a-z0-9]+(?:-[a-z0-9]+)*)" data-spec-anchor="(canonical|alias)"></a>$')

#: Not searched. Everything else tracked is, because a citation is load-bearing wherever it is
#: written: a test asserting `03` §5.5's rule and a contribution guide explaining it both go stale when
#: that section is rewritten. Listing directories instead left **234 citations across 38 files**
#: unreachable -- every instruction file, every root document and every test -- so the one tool that
#: finds what a change invalidates could not name the documents a sweep later found stale.
SKIPPED = ("nwb_lake_poc_docs/",)


def sections(path: Path) -> list[tuple[int, str, str]]:
    """Every numbered heading in a part, as (line, number, title)."""
    found = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if m := HEADING.match(line):
            found.append((n, m.group(1), m.group(2).strip()))
    return found


def touched(ref: str | None) -> dict[str, set[str]]:
    """Which section of which part each changed line falls in."""
    args = ["git", "diff", "--unified=0"] + ([ref] if ref else []) + ["--", "spec/parts"]
    diff = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False).stdout
    changed: dict[str, set[str]] = defaultdict(set)
    part = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            name = Path(line[6:]).name
            part = name if re.match(r"\d\d_", name) and "Implementation_Spec" not in name else None
        elif line.startswith("@@") and part:
            if m := re.search(r"\+(\d+)(?:,(\d+))?", line):
                start, count = int(m.group(1)), int(m.group(2) or 1)
                marks = sections(PARTS / part)
                for at in range(start, start + max(count, 1)):
                    prior = [s for s in marks if s[0] <= at]
                    if prior:
                        changed[part[:2]].add(prior[-1][1])
    return changed


@functools.cache
def index() -> dict[tuple[str, str], tuple[str, ...]]:
    """Every citation of a part section in the searched trees, as (part, section) to `path:line`.

    One pass over the tree, not one per section: a commit changing 51 sections walked it 51 times.
    """
    found: dict[tuple[str, str], list[str]] = defaultdict(list)
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    for name in listed:
        # The combined rendering is generated from the parts, so a citation inside it is one of
        # theirs counted twice.
        if name.startswith(SKIPPED) or "Implementation_Spec" in name:
            continue
        path = ROOT / name
        if path.suffix not in {".py", ".md", ".json"} or not path.is_file():
            continue
        try:
            lines = path.read_text().splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(lines, 1):
            for m in CITATION.finditer(line):
                found[m.group(1) or m.group(2), m.group(3)].append(f"{name}:{n}")
    return {key: tuple(value) for key, value in found.items()}


def citers(part: str, section: str) -> list[str]:
    """Every file citing this part and section, as `path:line`."""
    return list(index().get((part, section), ()))


def anchor_location(anchor: str) -> tuple[str, str, str] | None:
    """Return the part, section, and title immediately following a canonical anchor."""
    for path in sorted(PARTS.glob("[0-9][0-9]_*.md")):
        pending: set[str] = set()
        fenced = False
        for line in path.read_text().splitlines():
            if line.startswith("```"):
                fenced = not fenced
                pending.clear()
                continue
            if fenced:
                continue
            if match := ANCHOR.fullmatch(line):
                if match.group(2) == "canonical":
                    pending.add(match.group(1))
                continue
            if anchor in pending and (heading := HEADING.fullmatch(line)):
                return path.name[:2], heading.group(1), heading.group(2).strip()
            if line.strip():
                pending.clear()
    return None


def anchor_citers(anchor: str) -> list[str]:
    """Return live files and lines that refer to an anchor identifier."""
    found = []
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    for name in listed:
        if name.startswith(("revisions/accepted/", *SKIPPED)) or "Implementation_Spec" in name:
            continue
        path = ROOT / name
        if path.suffix not in {".py", ".md", ".json", ".toml"} or not path.is_file():
            continue
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if anchor in line and not ANCHOR.fullmatch(line):
                found.append(f"{name}:{number}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ref", nargs="?", help="Git revision or range to compare with the working tree")
    parser.add_argument(
        "--anchor",
        action="append",
        default=[],
        metavar="ID",
        help="also report one canonical stable anchor",
    )
    parser.add_argument(
        "--section",
        action="append",
        default=[],
        metavar="PART:SECTION",
        help="also report one explicit section, for example 02:7.1",
    )
    args = parser.parse_args()
    changed = touched(args.ref)
    for value in args.section:
        match = re.fullmatch(r"(\d\d):(\d+(?:\.\d+)*)", value)
        if match is None:
            parser.error(f"--section expects PART:SECTION, got {value!r}")
        part, section = match.groups()
        files = sorted(PARTS.glob(f"{part}_*.md"))
        if not files:
            parser.error(f"--section names absent Part {part}")
        declared = {number for _, number, _ in sections(files[0])}
        if section not in declared:
            parser.error(f"--section names absent Part {part} §{section}")
        changed[part].add(section)
    anchor_reports = []
    for anchor in args.anchor:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", anchor):
            parser.error(f"--anchor expects a lowercase hyphenated identifier, got {anchor!r}")
        location = anchor_location(anchor)
        if location is None:
            parser.error(f"--anchor names no canonical numbered-part anchor: {anchor}")
        anchor_reports.append((anchor, location, anchor_citers(anchor)))
    if not changed and not anchor_reports:
        print("no part changed" + (f" since {args.ref}" if args.ref else " in the working tree"))
        return 0
    total = 0
    for part in sorted(changed):
        titles = {n: t for _, n, t in sections(PARTS / next(p.name for p in PARTS.glob(f"{part}_*.md")))}
        for section in sorted(changed[part], key=lambda s: [int(x) for x in s.split(".")]):
            who = citers(part, section)
            total += len(who)
            head = f"`{part}` §{section}  {titles.get(section, '')}"
            print(f"\n{head}\n{'-' * len(head)}")
            print("  cited by nothing" if not who else "\n".join(f"  {w}" for w in who))
    for anchor, (part, section, title), who in anchor_reports:
        total += len(who)
        head = f"#{anchor}  Part {part} §{section}  {title}"
        print(f"\n{head}\n{'-' * len(head)}")
        print("  cited by nothing" if not who else "\n".join(f"  {site}" for site in who))
    print(
        f"\n{sum(len(v) for v in changed.values())} section(s) changed, "
        f"{len(anchor_reports)} anchor(s) queried, {total} citation(s) to read"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
