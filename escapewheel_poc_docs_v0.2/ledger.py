"""Every accepted normative clause has a disposition, or the compilation fails.

Two independent audits of this specification found dropped clauses, and found different ones:
`R53 §2.4`'s escape to `int64` vanished, `R21`'s codec floor vanished, `R36 §2.2`'s prefix digest
was reversed into "undefined", `R52`'s SHOULD became a MUST. Each was invisible because the
revision is cited elsewhere in the spec, so a citation sweep sees it and a reader does not.

The fix is a ledger rather than another audit. Every clause of every accepted revision that
carries RFC 2119 force appears in `applied.toml` with one of four dispositions:

    applied         stated in the compiled spec; `where` lists the parts and sections
    registry        delegated to registry/logical_schemas.json or rules.json
    superseded      a later revision replaced it; `by` names which
    rationale       decided nothing, so there is nothing to place

A clause binding a writer, reader, validator or consumer is `applied` like any other: an actor
is bound by the spec's prose, so naming one does not excuse a clause from appearing in a part.
There was a fifth disposition, `implementation`, which said a clause "binds a writer, reader or
validator rather than the prose" and so let 23 of them be counted as disposed while living
nowhere in the durable document. 21 were in a part or the registry all along and the ledger had
simply never recorded where; 2 had reached no part, which is the class this script exists to
catch and which that disposition hid. `applied` now requires a `where`.

A clause with no entry is **undisposed**, and this script exits non-zero listing them. Adding a
revision therefore adds failures until someone says where each of its clauses went, which is the
property neither audit had.

An `applied` entry's `where` is a list of `{ part, section }` targets, each with an optional `note`
saying which piece of the clause landed there. Every one is resolved against that part's own
headings, through `moves.toml`, so a clause cannot be recorded as placed in a section that does not
exist -- the defect one step along from no `where` at all, and the one that let R111 §3.5 name two
sections of `01` that part has never carried.

The other dispositions leave `where` free text or absent, because nothing resolves it: a `registry`
entry names the artifact that carries the clause, and `superseded` names its replacement in `by`.

    python ledger.py            # report
    python ledger.py --summary  # counts only
"""

from __future__ import annotations

import argparse
import functools
import re
from pathlib import Path

import tomllib

from moves import resolve

HERE = Path(__file__).resolve().parent
REVISIONS = HERE.parent / "revisions"
LEDGER = HERE / "applied.toml"

DISPOSITIONS = {"applied", "registry", "superseded", "rationale"}

#: `## 3.` and `### 3.1 ` alike, which is every section a part declares.
HEADING = re.compile(r"^#{1,4} (\d+(?:\.\d+)*)\.?(?:\s|$)", re.MULTILINE)


def targets(where: object) -> tuple[list[tuple[str, str]], list[str]]:
    """Each (part, section) an `applied` entry's `where` names, and every target that is malformed.

    A target is a table of `part` and `section`, with an optional `note` saying which piece of the
    clause landed there. The field was prose until the shape was pinned, and the cost was that
    every consumer parsed it differently and partially -- a field naming two parts read as naming
    none, and a pattern scanning one for two adjacent digits read `05 §10 §12` as part 05 and then
    part **10**, inventing a target in the same pass as it lost a real one.
    """
    if not isinstance(where, list):
        return [], [f"{where!r}, which is not a list of targets"]
    found, malformed = [], []
    for target in where:
        if (isinstance(target, dict) and isinstance(target.get("part"), str)
                and isinstance(target.get("section"), str)):
            found.append((target["part"], target["section"]))
        else:
            malformed.append(f"{target!r}, which is not a `part` and a `section`")
    return found, malformed


@functools.cache
def sections(part: str) -> frozenset[str] | None:
    """Every section number a part declares, or None where no part carries that number."""
    found = sorted(HERE.glob(f"{part}_*.md"))
    return frozenset(HEADING.findall(found[0].read_text())) if found else None


def unresolved(ledger: dict[str, dict]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Every `applied` target naming no section, and every one that is not a target at all."""
    dangling, unparsed = [], []
    for key, entry in sorted(ledger.items(), key=lambda kv: int(kv[0][1:].split()[0])):
        if entry.get("disposition") != "applied":
            continue
        found, loose = targets(entry.get("where", []))
        unparsed += [(key, piece) for piece in loose]
        for part, section in found:
            declared = sections(part)
            if declared is None:
                dangling.append((key, f"`{part}` — no part has that number"))
            # The move table is consulted only where the section is absent, as `check_citations.py`
            # consults it: a number that still exists means what it says, whatever has moved.
            elif section not in declared and resolve(part, section) not in declared:
                dangling.append((key, f"`{part}` §{section} — that part declares no such section"))
    return dangling, unparsed


def clauses() -> dict[str, str]:
    """Every Decision clause of every accepted revision, as `R<n> §<sec>` to its title.

    Everything a revision decided, not only what carries an RFC 2119 keyword. `R68 §2.1` says
    `pts` *becomes* `int64` and binds a writer completely without one; filtering on MUST and
    SHOULD missed it, and missed `R6 §2` entirely because that revision states its decision at
    the section level with no subsections. A clause that turns out to be rationale is disposed
    as such, which is a judgement someone recorded rather than a heuristic that dropped it.
    """
    found = {}
    for path in sorted(REVISIONS.glob("R*.md"), key=lambda p: int(re.match(r"R(\d+)", p.name).group(1))):
        number = re.match(r"R(\d+)", path.name).group(1)
        text = path.read_text()
        if "**Accepted**" not in text[:400]:
            continue
        # Every section from 2 onward, at either depth. Section 1 is Motivation by convention;
        # after that the numbering is not consistent -- R32 states its rules in §2, §3 and §4,
        # R30's order is §3.2, R21's codec floor is §3 -- so position cannot say what binds.
        # A subsection supersedes its parent: `### 2.1` is disposed, `## 2.` then is not.
        matches = [m for m in re.finditer(r"^#{2,3} (\d+(?:\.[\d.]*\d)?)\.?\s+(.+)$", text, re.MULTILINE)
                   if int(m.group(1).split(".")[0]) >= 2]
        parents = {m.group(1).split(".")[0] for m in matches if "." in m.group(1)}
        for index, match in enumerate(matches):
            section = match.group(1)
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end():end]
            # A parent is enumerated only for its own body, the text before its first
            # subsection. R32 §4 states the manifest's carry-forward there and then subdivides;
            # skipping every parent lost it.
            if section in parents and not re.search(r"\b(MUST|SHOULD)\b", body):
                continue
            # A Decision subsection always counts: `R68 §2.1` says `pts` *becomes* `int64` and
            # binds completely without an RFC 2119 keyword. Anywhere else -- and the numbering
            # is not consistent, R32 decides in §2, §3 and §4 -- a keyword is what marks it.
            if section.startswith("2") or re.search(r"\b(MUST|SHOULD)\b", body):
                found[f"R{number} §{section}"] = match.group(2).strip()
    return found


def recorded() -> dict[str, dict[str, str]]:
    """What the ledger says, keyed the same way."""
    if not LEDGER.exists():
        return {}
    text = LEDGER.read_text()
    try:
        return tomllib.loads(text).get("clause", {})
    except tomllib.TOMLDecodeError as exc:
        # Appending an entry that already exists is the usual cause, and tomllib's traceback
        # says so only in its last line.
        raise SystemExit(f"{LEDGER.name}: {exc}") from None


def main() -> int:
    """Report every clause with no disposition, and every disposition naming no clause."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--summary", action="store_true", help="counts only")
    args = parser.parse_args()

    binding, ledger = clauses(), recorded()
    # The ratchet's high-water mark lives beside the data it describes, not as a number in
    # another file that someone has to remember to lower. Falling below it rewrites it, so
    # disposing a clause shows up as a diff and `verify.py`'s clean-tree stage sees it.
    baseline = tomllib.loads(LEDGER.read_text()).get("baseline", {}).get("undisposed", 0) if LEDGER.exists() else 0
    undisposed = {k: v for k, v in binding.items() if k not in ledger}
    # A disposition for a clause that no longer exists is as wrong as a missing one: the revision
    # was edited, or the clause was renumbered, and the ledger now vouches for nothing.
    stale = sorted(set(ledger) - set(binding))
    bad = {k: d.get("disposition") for k, d in ledger.items()
           if d.get("disposition") not in DISPOSITIONS}
    # An `applied` entry naming no part says the clause was written down and not where, which is
    # the state the withdrawn `implementation` disposition made permanent for 23 clauses.
    placeless = sorted(k for k, d in ledger.items()
                       if d.get("disposition") == "applied" and not d.get("where"))
    dangling, unparsed = unresolved(ledger)

    counts: dict[str, int] = {}
    for entry in ledger.values():
        counts[entry.get("disposition", "?")] = counts.get(entry.get("disposition", "?"), 0) + 1
    print(f"{len(binding)} decision clauses across the accepted revisions")
    for name in sorted(counts):
        print(f"  {counts[name]:>4}  {name}")
    print(f"  {len(undisposed):>4}  undisposed")

    # Undisposed clauses are a backlog and can run to hundreds, so `--summary` holds them back.
    # The rest are defects in what the ledger already claims, and there is nothing to read
    # instead of them.
    if not args.summary:
        for key, title in sorted(undisposed.items(), key=lambda kv: (int(kv[0][1:].split()[0]), kv[0])):
            print(f"    UNDISPOSED  {key:<12} {title[:62]}")
    for key in stale:
        print(f"    STALE       {key:<12} the ledger disposes a clause no revision states")
    for key, value in sorted(bad.items()):
        print(f"    BAD         {key:<12} disposition {value!r} is not one of {sorted(DISPOSITIONS)}")
    for key in placeless:
        print(f"    PLACELESS   {key:<12} applied, but `where` names no part")
    for key, target in dangling:
        print(f"    DANGLING    {key:<12} {target}")
    for key, piece in unparsed:
        print(f"    MALFORMED   {key:<12} `where` holds {piece}")

    over = max(0, len(undisposed) - baseline)
    failures = over + len(stale) + len(bad) + len(placeless) + len(dangling) + len(unparsed)
    if len(undisposed) < baseline:
        text = LEDGER.read_text()
        LEDGER.write_text(re.sub(r"(?m)^undisposed = \d+$", f"undisposed = {len(undisposed)}", text))
        print(f"\nratchet lowered: {baseline} -> {len(undisposed)}; commit applied.toml")
        return 0
    if not failures:
        print(f"\nok — {len(undisposed)} undisposed, at the recorded high-water mark")
    elif over:
        print(f"\n{over} clause(s) need a disposition; the mark is {baseline}")
    else:
        print(f"\n{failures} disposition(s) vouch for something that is not there")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
