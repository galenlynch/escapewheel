"""A citation of a requirement names the part that states it, not the revision that introduced it.

`00` §10.1 binds every citation of a requirement in an implementation's source. `check_citations.py`
answers whether a citation resolves; this answers whether it points at the right kind of document,
which no other tool can see -- a citation of a revision clause that landed in a part resolves
perfectly and still sends a reader to the change record.

The ledger is the map. Where `applied.toml` disposes a clause `applied`, its `where` names the part
and section that states it, so the replacement is mechanical: `R88 §2.1` becomes `02` §7.1.

What is not mechanical is whether a citation is of the **requirement** or of the **reasoning**, and
`00` §10.2 permits the second. So a citation that stays carries a reason in `EXEMPT`, keyed by the
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
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "escapewheel_poc_docs_v0.2" / "applied.toml"

#: `R92 §2.2`. The same spelling `check_citations.py` resolves.
REVISION = re.compile(r"\bR(\d+) §(\d+(?:\.\d+)*)")
#: A `where` naming a part and section: "02_core_logical_schemas.md §7.1".
WHERE = re.compile(r"^(\d\d)_\w+\.md §(\d+(?:\.\d+)*)$")

#: Sites where naming a revision is the point, each with why. A pattern is matched against the
#: whole line. Every entry is checked to still match something, so a site that goes away takes
#: its exemption with it rather than leaving a permanent excuse behind.
EXEMPT: tuple[tuple[str, str, str], ...] = (
    ("registry/build.py", r'SINCE\[0\] = "',
     "the stamp that becomes a column's `since`, whose value names a revision by design (`02` §9.4)"),
    ("registry/build.py", r'since="',
     "the same stamp, written inline on a column"),
    ("registry/build.py", r"^\s*# ----",
     "a block marker saying which revision's block follows; the file is organised by revision"),
    ("escapewheel_poc_docs_v0.2/ledger.py", r".",
     "the ledger keys on revision clauses, which is what makes it the map `00` §10.1 resolves through"),
    ("revisions/", r".",
     "a revision citing another revision (`00` §10.2)"),
)

#: Individual citations of the **reasoning** a part does not carry, which `00` §10.2 permits: a
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
)


def ledger() -> dict[str, str]:
    """Each clause disposed `applied`, mapped to the `NN §S` citation that states it."""
    clauses = tomllib.loads(LEDGER.read_text())["clause"]
    out = {}
    for key, entry in clauses.items():
        if entry.get("disposition") != "applied":
            continue
        found = WHERE.match(entry.get("where", ""))
        if found:
            out[key] = f"`{found.group(1)}` §{found.group(2)}"
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
        for name, number, key, target in sorted({(n, ln, k, t) for n, ln, k, t, _ in found}):
            print(f"  {name}:{number}  {key} → {target}")
    by_file = len({name for name, *_ in found})
    print(f"{len(found)} citation(s) of a requirement name a revision, across {by_file} file(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
