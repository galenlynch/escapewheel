"""A citation of a requirement names the part that states it, not the revision that introduced it.

Part 00 §10.1 binds every citation of a requirement in an implementation's source. `check_citations.py`
answers whether a citation resolves; this answers whether it points at the right kind of document,
which no other tool can see -- a citation of a revision clause that landed in a part resolves
perfectly and still sends a reader to the change record.

The ledger is the map. Where `applied.toml` disposes a clause `applied`, its `where` lists the parts
and sections that state it, so the replacement is mechanical: `R88 §2.1` becomes Part 02 §7.1.

Only a clause disposed `applied` is reported. A clause the registry carries is read from the
registry, one disposed `rationale` decided nothing and so states no requirement, and a Motivation
or an Open section is the reasoning itself -- Part 00 §10.2 sends a reader to the revision for all
three, so they are not citations Part 00 §10.1 binds.

What is not mechanical is whether a citation of an `applied` clause is of the **requirement** or of
the **reasoning** behind it, and Part 00 §10.2 permits the second. So a citation that stays carries a reason in `EXEMPT`, keyed by the
shape or the site rather than left to be rediscovered -- `registry/check.py`'s discipline for
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
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "escapewheel_poc_docs_v0.2" / "applied.toml"

#: `R92 §2.2`. The same spelling `check_citations.py` resolves.
REVISION = re.compile(r"\bR(\d+) §(\d+(?:\.\d+)*)")

#: Sites where naming a revision is the point, each with why. A pattern is matched against the
#: whole line. Every entry is checked to still match something, so a site that goes away takes
#: its exemption with it rather than leaving a permanent excuse behind.
EXEMPT: tuple[tuple[str, str, str], ...] = (
    ("registry/build.py", r'SINCE\[0\] = "',
     "the stamp that becomes a column's `since`, whose value names a revision by design (Part 02 §9.4)"),
    ("registry/build.py", r'since="',
     "the same stamp, written inline on a column"),
    ("registry/", r"^\s*# ----",
     "a block marker saying which revision's block follows; both files are organised by revision"),
    ("escapewheel_poc_docs_v0.2/ledger.py", r".",
     "the ledger keys on revision clauses, which is what makes it the map Part 00 §10.1 resolves through"),
    ("revisions/", r".",
     "a revision citing another revision (Part 00 §10.2)"),
)


#: Individual citations of the **reasoning** a part does not carry, which Part 00 §10.2 permits: a
#: measurement, or what a revision did to the format on its way to the present. Keyed by file and
#: clause rather than by line, since a line number moves and this pairing does not.
REASONING: tuple[tuple[str, str, str], ...] = (
    ("escapewheel-reader/src/escapewheel_reader/packet.py", "R86 §2.4",
     "the measurement that a scalar projection beats a join, not the rule it justified"),
    ("escapewheel-writer/src/escapewheel_writer/recipe.py", "R108 §3.4",
     "which preference was struck and why, which no part records"),
    ("escapewheel-writer/src/escapewheel_writer/sources/nwb.py", "R87 §2.8",
     "what the adapter did before the clause landed"),
    ("escapewheel-writer/src/escapewheel_writer/sources/sync.py", "R37 §3.1",
     "the neighbour count a local rate was measured over"),
    ("escapewheel-writer/src/escapewheel_writer/sources/sync.py", "R37 §3.2",
     "the revision's own terminal-anchor test, which is the measurement rather than the rule"),
    ("escapewheel-writer/tests/test_arbitration.py", "R108 §3.4",
     "the count that class held before and after the entry was struck"),
    ("escapewheel-writer/tests/test_writer.py", "R108 §3.4",
     "the same, at the site the struck entry used to reach"),
    ("registry/build.py", "R67 §2.1",
     "what that revision gave the device chain, and where it stopped"),
    ("registry/build.py", "R65 §2.1",
     "what that revision gave the array tables, and what it skipped"),
    ("registry/build.py", "R81 §2.4",
     "which columns the old override named, which is why the current one has five"),
    ("escapewheel-reader/src/escapewheel_reader/ordering.py", "R81 §2.4",
     "what narrowed the override, beside the citation of the override itself"),
    ("escapewheel-aind/src/escapewheel_aind/nwb.py", "R59 §2",
     "which of the four atlas fields that revision promoted to columns, and which it left"),
    ("escapewheel-aind/tests/nwbfixture.py", "R59 §2",
     "the same, at the fixture that supplies all four"),
    ("escapewheel-aind/tests/test_nwb_dialect.py", "R59 §2",
     "the same, at the test that asserts which two leave the bag"),
    ("fixtures/corpus.py", "R82 §2",
     "that the two rules changed level, which is why no advisory pass is needed here"),
    ("registry/build.py", "R54 §2",
     "what that revision gave `core.intervals`, and what had nowhere to go before it"),
)


def cited(entry: dict) -> list[str]:
    """Each target of an `applied` entry, spelled as Part 00 §10.4 requires: Part 02 §7.1."""
    return [f"Part {t['part']} §{t['section']}" for t in entry.get("where", [])]


def rollup(clauses: dict[str, dict]) -> dict[str, list[str]]:
    """Each section-level key, mapped to every part section its own subsections landed in.

    The ledger keys on subsections, so a citation naming a whole Decision -- `R40 §2` where the
    ledger holds `R40 §2.1` -- matched no entry and passed unchecked. 29 citations were that shape.
    """
    out: dict[str, list[str]] = {}
    for key, entry in clauses.items():
        if entry.get("disposition") != "applied":
            continue
        parent = key.split(".")[0] if "." in key.split("§")[1] else None
        if parent is None:
            continue
        for candidate in cited(entry):
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
    out = {}
    for key, entry in clauses.items():
        if entry.get("disposition") != "applied":
            continue
        found = cited(entry)
        if found:
            out[key] = found
    out.update({k: v for k, v in rollup(clauses).items() if k not in out})
    return out


def tracked() -> list[str]:
    """Every tracked Python file, relative to the repository root."""
    listed = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout.split()
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
    ap.add_argument("--exempt", action="store_true", help="the exemptions and whether each is needed")
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
