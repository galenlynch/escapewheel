"""A citation of a requirement names the part that states it, not the revision that introduced it.

`revisions/CONTRIBUTING.md#ew-citation-context` binds every current requirement citation in an
implementation's source. `check_citations.py`
answers whether a citation resolves; this answers whether it points at the right kind of document,
which no other tool can see -- a citation of a revision clause that landed in a part resolves
perfectly and still sends a reader to the change record.

The ledger is the map. Where `applied.toml` disposes a clause `applied`, its `where` lists the parts
and sections that state it, so the replacement is mechanical: `R88 §2.1` becomes Part 02 §7.1.

Only a clause disposed `applied` is reported. A clause the registry carries is read from the
registry, one disposed `rationale` decided nothing and so states no requirement, and a Motivation
or an Open section is the reasoning itself, so the current-owner rule does not bind those
citations.

What is not mechanical is whether a citation of an `applied` clause is of the **requirement** or of
the **reasoning** behind it, which the current citation-context rule permits. So a citation that
stays carries a reason in `EXEMPT`, keyed by the
shape or the site rather than left to be rediscovered -- `spec/tools/conventions.py`'s discipline for
`NAMING_EXCEPTIONS`, whose entries are checked to still be needed so the list cannot go stale.

    python repoint.py              # every citation that should name a part and does not
    python repoint.py --exempt     # the exemptions, and any that no longer match anything
    python repoint.py --quiet      # counts only
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "revisions" / "applied.toml"
HEADINGS = ROOT / "spec" / "tools" / "headings.toml"

#: `R92 §2.2`. The same spelling `check_citations.py` resolves.
REVISION = re.compile(r"\bR(\d+) §(\d+(?:\.\d+)*)")

#: Sites where naming a revision is the point, each with why. A pattern is matched against the
#: whole line. Every entry is checked to still match something, so a site that goes away takes
#: its exemption with it rather than leaving a permanent excuse behind.
EXEMPT: tuple[tuple[str, str, str], ...] = (
    (
        "revisions/ledger.py",
        r".",
        "the ledger keys on revision clauses, as `revisions/CONTRIBUTING.md#ew-current-owner-ledger` defines",
    ),
    ("revisions/", r".", "a revision citing another revision as historical context"),
)


#: Individual citations of the **reasoning** a current owner does not carry, which
#: `revisions/CONTRIBUTING.md#ew-citation-context` permits: a
#: measurement, or what a revision did to the format on its way to the present. Keyed by file and
#: clause rather than by line, since a line number moves and this pairing does not.
REASONING: tuple[tuple[str, str, str], ...] = (
    (
        "escapewheel-reader/src/escapewheel_reader/packet.py",
        "R86 §2.4",
        "the measurement that a scalar projection beats a join, not the rule it justified",
    ),
    (
        "escapewheel-writer/src/escapewheel_writer/sources/nwb.py",
        "R87 §2.8",
        "what the adapter did before the clause landed",
    ),
    (
        "escapewheel-writer/src/escapewheel_writer/sources/sync.py",
        "R37 §3.1",
        "the neighbour count a local rate was measured over",
    ),
    (
        "escapewheel-writer/src/escapewheel_writer/sources/sync.py",
        "R37 §3.2",
        "the revision's own terminal-anchor test, which is the measurement rather than the rule",
    ),
    (
        "escapewheel-aind/src/escapewheel_aind/nwb.py",
        "R59 §2",
        "which of the four atlas fields that revision promoted to columns, and which it left",
    ),
    (
        "escapewheel-aind/tests/nwbfixture.py",
        "R59 §2",
        "the same, at the fixture that supplies all four",
    ),
    (
        "escapewheel-aind/tests/test_nwb_dialect.py",
        "R59 §2",
        "the same, at the test that asserts which two leave the bag",
    ),
    (
        "fixtures/corpus.py",
        "R82 §2",
        "that the two rules changed level, which is why no advisory pass is needed here",
    ),
)


def anchors() -> dict[str, dict]:
    """Each canonical anchor's current part and section, as `headings.py` records them."""
    return tomllib.loads(HEADINGS.read_text()).get("anchor", {})


def cited(entry: dict, located: dict[str, dict] | None = None) -> list[str]:
    """Each part target of an applied entry, in current citation form.

    An anchor target resolves to the section it now heads; skipping it would exempt every citation
    of a clause whose landing moved to an anchor.
    """
    located = anchors() if located is None else located
    out = []
    for target in entry.get("where", []):
        if "part" not in target:
            continue
        if "section" in target:
            out.append(f"Part {target['part']} §{target['section']}")
        elif (where := located.get(target.get("anchor", ""))) is not None:
            out.append(f"Part {where['part']} §{where['section']}")
    return out


def rollup(clauses: dict[str, dict]) -> dict[str, list[str]]:
    """Each section-level key, mapped to every part section its own subsections landed in.

    The ledger keys on subsections, so a citation naming a whole Decision -- `R40 §2` where the
    ledger holds `R40 §2.1` -- matched no entry and passed unchecked. 29 citations were that shape.
    """
    out: dict[str, list[str]] = {}
    located = anchors()
    for key, entry in clauses.items():
        if entry.get("disposition") != "applied":
            continue
        parent = key.split(".")[0] if "." in key.split("§")[1] else None
        if parent is None:
            continue
        for candidate in cited(entry, located):
            if candidate not in out.setdefault(parent, []):
                out[parent].append(candidate)
    return {k: v for k, v in out.items() if k not in clauses and v}


def ledger() -> dict[str, list[str]]:
    """Each clause disposed `applied`, mapped to every `NN §S` citation that states it.

    A clause landing in one place has one candidate and the repoint is mechanical. One landing in
    several has no single answer, so the list is returned whole and the citation is reported for a
    decision rather than rewritten -- which is what a `where` naming two parts used to buy: the
    citation passed unseen, because a single-match pattern read the field as naming nothing.
    """
    clauses = tomllib.loads(LEDGER.read_text())["clause"]
    located = anchors()
    out = {}
    for key, entry in clauses.items():
        if entry.get("disposition") != "applied":
            continue
        found = cited(entry, located)
        if found:
            out[key] = found
    out.update({k: v for k, v in rollup(clauses).items() if k not in out})
    return out


def tracked() -> list[str]:
    """Every working-tree Python file, relative to the repository root."""
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [name for name in listed if (ROOT / name).is_file()]


def exemption(name: str, line: str, key: str) -> str | None:
    """The reason this citation may name a revision, if one applies."""
    for prefix, pattern, reason in EXEMPT:
        if name.startswith(prefix) and re.search(pattern, line):
            return reason
    for site, clause, reason in REASONING:
        if name == site and key == clause:
            return reason
    return None


def findings() -> tuple[list[tuple[str, int, str, str, str]], dict[tuple[str, str], int]]:
    """Every citation that should name a part, and how often each exemption fired."""
    parts, used = ledger(), {(p, q): 0 for p, q, _ in EXEMPT + REASONING}
    out = []
    for name in tracked():
        for number, line in enumerate((ROOT / name).read_text(errors="replace").splitlines(), 1):
            for match in REVISION.finditer(line):
                key = f"R{match.group(1)} §{match.group(2)}"
                if key not in parts:
                    continue
                if exemption(name, line, key) is not None:
                    for prefix, pattern, _ in EXEMPT:
                        if name.startswith(prefix) and re.search(pattern, line):
                            used[prefix, pattern] += 1
                            break
                    else:
                        used[name, key] += 1
                    continue
                out.append((name, number, key, parts[key], line.strip()))
    return out, used


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument(
        "--exempt",
        action="store_true",
        help="the exemptions and whether each is needed",
    )
    ap.add_argument("--quiet", action="store_true", help="counts only")
    args = ap.parse_args()

    found, used = findings()

    if args.exempt:
        for prefix, pattern, reason in EXEMPT + REASONING:
            count = used[prefix, pattern]
            mark = "     " if count else "STALE"
            print(f"  {mark} {prefix} · {pattern} — {count} site(s)\n        {reason}")
        stale = sum(1 for e in EXEMPT + REASONING if not used[e[0], e[1]])
        print(f"\n{len(EXEMPT) + len(REASONING)} exemption(s), {stale} matching nothing")
        return 1 if stale else 0

    if not args.quiet:
        for name, number, key, targets in sorted({(n, ln, k, tuple(t)) for n, ln, k, t, _ in found}):
            arrow = targets[0] if len(targets) == 1 else " or ".join(targets) + "  (choose)"
            print(f"  {name}:{number}  {key} → {arrow}")
    by_file = len({name for name, *_ in found})
    print(f"{len(found)} citation(s) of a requirement name a revision, across {by_file} file(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
