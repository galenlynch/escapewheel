"""Who cites the specification sections a change touches.

A part's section is the statement of record, so editing one silently invalidates whatever pointed
at it. Part 03 §5.5 carries 15 citations across the writer, the parts and the revisions, and R110
rewrote it without any of them being read. `check_citations.py` answers the other direction — does
this citation resolve — and cannot see that a resolved citation now points at different prose.

    python revisions/impact.py              # what the working tree changes, and who cites it
    python revisions/impact.py HEAD~3       # the same for a commit range

Reports each changed section with every file that cites it. It says nothing about whether a citer
is stale, which needs reading: what it removes is having to find them first.
"""

from __future__ import annotations

import functools
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "escapewheel_poc_docs_v0.2"

#: A heading that opens a numbered section, at any depth.
HEADING = re.compile(r"^#{2,4} (\d+(?:\.\d+)*)\.? +(.+)$")

#: `Part 03 §5.4`, which Part 00 §10.4 requires, and the bare `03` §5.4 it replaced: a citation
#: written before that clause still resolves, so both are read here.
CITATION = re.compile(r"(?:`(\d\d)`|Part (\d\d))\s+§(\d+(?:\.\d+)*)")

#: Searched for citers. The combined rendering is excluded: it is generated from the parts, so a
#: citation inside it is one of theirs counted twice.
SEARCHED = ("escapewheel-reader/src", "escapewheel-writer/src", "escapewheel-validator/src",
            "registry", "conformance", "fixtures", "revisions", "escapewheel_poc_docs_v0.2")


def sections(path: Path) -> list[tuple[int, str, str]]:
    """Every numbered heading in a part, as (line, number, title)."""
    found = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if m := HEADING.match(line):
            found.append((n, m.group(1), m.group(2).strip()))
    return found


def touched(ref: str | None) -> dict[str, set[str]]:
    """Which section of which part each changed line falls in."""
    args = ["git", "diff", "--unified=0"] + ([ref] if ref else []) + ["--", "escapewheel_poc_docs_v0.2"]
    diff = subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout
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
    for root in SEARCHED:
        for path in sorted((ROOT / root).rglob("*")):
            if path.suffix not in {".py", ".md", ".json"} or ".venv" in str(path):
                continue
            if "Implementation_Spec" in path.name:
                continue
            try:
                lines = path.read_text().splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(lines, 1):
                for m in CITATION.finditer(line):
                    found[m.group(1) or m.group(2), m.group(3)].append(f"{path.relative_to(ROOT)}:{n}")
    return {key: tuple(value) for key, value in found.items()}


def citers(part: str, section: str) -> list[str]:
    """Every file citing this part and section, as `path:line`."""
    return list(index().get((part, section), ()))


def main() -> int:
    ref = sys.argv[1] if len(sys.argv) > 1 else None
    changed = touched(ref)
    if not changed:
        print("no part changed" + (f" since {ref}" if ref else " in the working tree"))
        return 0
    total = 0
    for part in sorted(changed):
        titles = {n: t for _, n, t in sections(PARTS / next(
            p.name for p in PARTS.glob(f"{part}_*.md")))}
        for section in sorted(changed[part], key=lambda s: [int(x) for x in s.split(".")]):
            who = citers(part, section)
            total += len(who)
            head = f"`{part}` §{section}  {titles.get(section, '')}"
            print(f"\n{head}\n{'-' * len(head)}")
            print("  cited by nothing" if not who else
                  "\n".join(f"  {w}" for w in who))
    print(f"\n{sum(len(v) for v in changed.values())} section(s) changed, {total} citation(s) to read")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
