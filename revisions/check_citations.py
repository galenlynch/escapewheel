"""Every citation in a revision or a draft resolves to a section that exists.

A citation is the load-bearing part of a revision: an implementer follows it to the rule. Nothing
checked them, and a wrong one is invisible to every other tool -- `ledger.py` sees that a clause
has a disposition, and a grep for the revision sees a document that exists. Four were found by hand
in one session: `02` §10.3 cited twice for a waiver that is §10.1's, R30 §3.2 credited with a
five-column layout it states in seven, `07` cited for an Iceberg deferral that is `00` §7.3's, and
six references to a draft's §5 left pointing at Consequence after it was restructured.

Three forms are resolved:

    R92 §2.2        against revisions/R92-*.md
    `03` §5.4       against escapewheel_poc_docs_v0.2/03_*.md
    §3.1            against the citing document itself

What fails the build is a revision-to-revision citation that does not resolve, anywhere, and a
part citation that does not resolve in a **draft**. A draft is what gets accepted next, so a broken
part citation there becomes a broken clause in the spec; an accepted revision is history, and the
early ones cite the frozen v0.1 numbering, which exists as headings in neither compiled spec.
Those are counted and shown, not failed.

An unprefixed `§N` that matches no local heading is reported and does not fail: it is usually a
reference whose antecedent is the previous clause ("R86 ... its §1.1"), which reads correctly and
resolves to nothing mechanically. Worth seeing, since the same shape is how a reference to another
document's §7.3 gets read as this document's §7.

    python check_citations.py            # report
    python check_citations.py --quiet    # errors only
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARTS = HERE.parent / "escapewheel_poc_docs_v0.2"

#: `## 3.` and `### 3.1 ` alike; the trailing dot is optional and the numbering may nest.
HEADING = re.compile(r"^#{1,4} (\d+(?:\.\d+)*)\.?(?:\s|$)", re.MULTILINE)
#: A revision's own number, from its filename.
NUMBER = re.compile(r"^R(\d+)-")
#: `R92 §2.2`, `R92 §2`. The section may end a sentence, so the trailing dot is trimmed.
REVISION = re.compile(r"\bR(\d+) §(\d+(?:\.\d+)*)")
#: "`03` §5.4" and "Part 03 §5.4".
PART = re.compile(r"(?:`(0\d)`|Part (0\d)) §(\d+(?:\.\d+)*)")
#: Any §, so the ones the two above did not claim can be treated as local.
ANY = re.compile(r"§(\d+(?:\.\d+)*)")


def headings(text: str) -> set[str]:
    """Every section number a document declares, at any depth."""
    return set(HEADING.findall(text))


def document(number: str) -> Path | None:
    """The accepted revision with this number, if one exists."""
    found = sorted(HERE.glob(f"R{number}-*.md"))
    return found[0] if found else None


def part(number: str) -> Path | None:
    """The v0.2 part with this number."""
    found = sorted(PARTS.glob(f"{number}_*.md"))
    return found[0] if found else None


def check(path: Path) -> tuple[list[str], list[str], list[str]]:
    """Return this document's unresolved revision citations, part citations and local references."""
    text = path.read_text()
    own = headings(text)
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
    for match in ANY.finditer(text):
        if any(a <= match.start() < b for a, b in spans):
            continue
        if match.group(1) not in own:
            loose.append(f"§{match.group(1)} — unprefixed, and this document has no such section")
    return errors, parts, sorted(set(loose))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--quiet", action="store_true", help="errors only")
    args = ap.parse_args()

    paths = sorted(HERE.glob("R*.md"), key=lambda p: int(NUMBER.match(p.name).group(1)))
    paths += sorted((HERE / "drafts").glob("*.md"))
    # An editor's lock file is a symlink to a target that never existed -- Emacs writes
    # `.#name.md -> user@host:pid`. Following one raises, so a full `verify.py` would fail for as
    # long as any tracked document is open. `is_file()` is false for a dangling link and true for
    # a real one, so this skips the lock and nothing else.
    paths = [p for p in paths if p.is_file()]
    broken, historical = 0, 0
    for path in paths:
        draft = path.parent.name == "drafts"
        errors, parts, loose = check(path)
        if draft:
            errors += parts
        else:
            historical += len(parts)
        broken += len(errors)
        for line in errors:
            print(f"  BROKEN  {path.name}: {line}")
        if not args.quiet:
            for line in parts if not draft else []:
                print(f"  v0.1    {path.name}: {line}")
            for line in loose:
                print(f"  loose   {path.name}: {line}")
    tail = f", {historical} citing the frozen v0.1 numbering" if historical else ""
    print(f"{len(paths)} documents, {broken} unresolved citation(s){tail}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
