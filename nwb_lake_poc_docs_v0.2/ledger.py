"""Every accepted normative clause has a disposition, or the compilation fails.

Two independent audits of this specification found dropped clauses, and found different ones:
`R53 §2.4`'s escape to `int64` vanished, `R21`'s codec floor vanished, `R36 §2.2`'s prefix digest
was reversed into "undefined", `R52`'s SHOULD became a MUST. Each was invisible because the
revision is cited elsewhere in the spec, so a citation sweep sees it and a reader does not.

The fix is a ledger rather than another audit. Every clause of every accepted revision that
carries RFC 2119 force appears in `applied.toml` with one of four dispositions:

    applied         stated in the compiled spec; `where` names the part
    registry        delegated to registry/logical_schemas.json, which the spec does not restate
    implementation  binds a writer, reader or validator rather than the prose
    superseded      a later revision replaced it; `by` names which

A clause with no entry is **undisposed**, and this script exits non-zero listing them. Adding a
revision therefore adds failures until someone says where each of its clauses went, which is the
property neither audit had.

    python ledger.py            # report
    python ledger.py --summary  # counts only
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import tomllib

HERE = Path(__file__).resolve().parent
REVISIONS = HERE.parent / "revisions"
LEDGER = HERE / "applied.toml"

DISPOSITIONS = {"applied", "registry", "implementation", "superseded", "rationale"}


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
        subsections = list(re.finditer(r"^### (2\.[\d.]*\d)\s+(.+)$", text, re.MULTILINE))
        for match in subsections:
            found[f"R{number} §{match.group(1)}"] = match.group(2).strip()
        # A revision whose Decision has no subsections states it at the section level.
        if not subsections and (whole := re.search(r"^## (2)\.\s+(.+)$", text, re.MULTILINE)):
            found[f"R{number} §{whole.group(1)}"] = whole.group(2).strip()
    return found


def recorded() -> dict[str, dict[str, str]]:
    """What the ledger says, keyed the same way."""
    if not LEDGER.exists():
        return {}
    return tomllib.loads(LEDGER.read_text()).get("clause", {})


def main() -> int:
    """Report every clause with no disposition, and every disposition naming no clause."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--summary", action="store_true", help="counts only")
    # A ratchet, not a gate. 137 clauses are undisposed today and clearing them is real work;
    # what must not happen is the number growing, which is what adding a revision does until
    # someone says where its clauses went. CI passes the current count and fails on 138.
    parser.add_argument("--max-undisposed", type=int, default=0,
                        help="tolerate this many undisposed clauses; more is a failure")
    args = parser.parse_args()

    binding, ledger = clauses(), recorded()
    undisposed = {k: v for k, v in binding.items() if k not in ledger}
    # A disposition for a clause that no longer exists is as wrong as a missing one: the revision
    # was edited, or the clause was renumbered, and the ledger now vouches for nothing.
    stale = sorted(set(ledger) - set(binding))
    bad = {k: d.get("disposition") for k, d in ledger.items()
           if d.get("disposition") not in DISPOSITIONS}

    counts: dict[str, int] = {}
    for entry in ledger.values():
        counts[entry.get("disposition", "?")] = counts.get(entry.get("disposition", "?"), 0) + 1
    print(f"{len(binding)} decision clauses across the accepted revisions")
    for name in sorted(counts):
        print(f"  {counts[name]:>4}  {name}")
    print(f"  {len(undisposed):>4}  undisposed")

    if not args.summary:
        for key, title in sorted(undisposed.items(), key=lambda kv: (int(kv[0][1:].split()[0]), kv[0])):
            print(f"    UNDISPOSED  {key:<12} {title[:62]}")
        for key in stale:
            print(f"    STALE       {key:<12} the ledger disposes a clause no revision states")
        for key, value in sorted(bad.items()):
            print(f"    BAD         {key:<12} disposition {value!r} is not one of {sorted(DISPOSITIONS)}")

    over = max(0, len(undisposed) - args.max_undisposed)
    failures = over + len(stale) + len(bad)
    if not failures:
        print(f"\nok — {len(undisposed)} undisposed, within the {args.max_undisposed} allowed")
    else:
        print(f"\n{failures} clause(s) need a disposition")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
