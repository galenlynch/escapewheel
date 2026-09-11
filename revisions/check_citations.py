"""Every citation resolves to a section that exists, and every part is numbered so one can.

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

Every tracked Python file is checked too, not only the revisions. `00` §10.1 sends a comment to the
part that states its rule, so a citation in the source is load-bearing in the same way -- and until
this scanned them, five were broken: four naming section 56 of Part 00 and section 92 of Part 01,
both v0.1 *line* numbers carried into section form, and one naming a section R70 never had. None
resolved and nothing reported them. A part citation that does not resolve in a tracked file is an
error, as in a draft: the source is live.

Those are spelled out in prose rather than written as citations, because this file is one of the
files it reads.

The parts are also checked for the numbering `00` §10.3 requires. `headings` returns a set, which is
what hid `05` carrying two sections numbered 11 through five accepted revisions -- a duplicate
vanishes into a set and the citation still resolves. Two sections with one number fail the build and
sections that do not ascend are reported, which is the MUST and the SHOULD of `00` §10.3.

    python check_citations.py            # report
    python check_citations.py --quiet    # errors only
"""

from __future__ import annotations

import argparse
import re
import subprocess
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
#: "`03` §5.4" and "Part 03 §5.4". Two digits, not `0` and a digit: R93 added Part 10, and a
#: pattern written before it read every `10` §x as an unprefixed local reference, which is the
#: bucket that does not fail the build.
PART = re.compile(r"(?:`(\d\d)`|Part (\d\d)) §(\d+(?:\.\d+)*)")
#: Any §, so the ones the two above did not claim can be treated as local.
ANY = re.compile(r"§(\d+(?:\.\d+)*)")


def headings(text: str) -> set[str]:
    """Every section number a document declares, at any depth."""
    return set(HEADING.findall(text))


def numbering(text: str) -> tuple[list[str], list[tuple[str, str]]]:
    """A part's repeated section numbers, and each adjacent pair that fails to ascend.

    Compared as tuples of integers, so `1.10` follows `1.9` and a nested section follows its
    parent. Every repeat is also a non-ascending pair; both are returned because `00` §10.3 makes
    the first an error and the second a report.
    """
    found = HEADING.findall(text)
    keys = [tuple(int(part) for part in number.split(".")) for number in found]
    repeated = sorted({n for n in found if found.count(n) > 1}, key=lambda n: keys[found.index(n)])
    descending = [(found[i], found[i + 1]) for i in range(len(keys) - 1) if keys[i + 1] <= keys[i]]
    return repeated, descending


def document(number: str) -> Path | None:
    """The accepted revision with this number, if one exists."""
    found = sorted(HERE.glob(f"R{number}-*.md"))
    return found[0] if found else None


def moved(number: str, section: str) -> str:
    """The section this one became, where a part has renumbered (`moves.toml`)."""
    import sys
    sys.path.insert(0, str(PARTS))
    from moves import resolve

    return resolve(number, section)


def part(number: str) -> Path | None:
    """The v0.2 part with this number."""
    found = sorted(PARTS.glob(f"{number}_*.md"))
    return found[0] if found else None


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
            if moved(name, section) not in headings(target.read_text()):
                parts.append(f"`{name}` §{section} — {target.name} has no §{section}")

    spans = [(a, b) for a, b in claimed]
    for match in ANY.finditer(text) if own is not None else ():
        if any(a <= match.start() < b for a, b in spans):
            continue
        if match.group(1) not in own:
            loose.append(f"§{match.group(1)} — unprefixed, and this document has no such section")
    return errors, parts, sorted(set(loose))


def sources() -> list[Path]:
    """Every tracked Python file, which is where a citation of a part has to resolve."""
    listed = subprocess.run(["git", "ls-files", "*.py"], cwd=HERE.parent,
                            capture_output=True, text=True, check=True).stdout.split()
    return [HERE.parent / name for name in listed if (HERE.parent / name).is_file()]


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
    code = sources()
    broken, historical = 0, 0

    # `00` §10.3's numbering, checked before any citation: a duplicate number makes a citation
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
        draft = path.parent.name == "drafts" or path.suffix == ".py"
        errors, parts, loose = check(path)
        if draft:
            errors += parts
        else:
            historical += len(parts)
        broken += len(errors)
        shown = path.relative_to(HERE.parent) if path.suffix == ".py" else path.name
        for line in errors:
            print(f"  BROKEN  {shown}: {line}")
        if not args.quiet:
            for line in parts if not draft else []:
                print(f"  v0.1    {shown}: {line}")
            for line in loose:
                print(f"  loose   {shown}: {line}")
    tail = f", {historical} citing the frozen v0.1 numbering" if historical else ""
    print(f"{len(paths)} documents and {len(code)} source files, "
          f"{broken} unresolved citation(s){tail}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
