"""Fill the counts in this repository's documents from the things they count.

A count typed by hand drifts from what it counts within days. Any working-tree Markdown file may
instead carry a region delimited by `<!-- BEGIN facts: NAME -->` and `<!-- END facts: NAME -->`,
which this script fills from the registry, the revisions and the corpus. `verify.py` runs it and
then checks that regeneration preserved the candidate state, so a stale count fails the build.

Test counts are not filled: they need the suites run, and a document only a five-minute job can
regenerate is regenerated less often than it changes.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "spec/artifacts/logical_schemas.json"
EXTENSIONS = (ROOT / "extensions", ROOT / "escapewheel-aind/extensions")

REGION = re.compile(r"(<!-- BEGIN facts: (\w+) -->\n).*?(<!-- END facts: \2 -->)", re.DOTALL)


def documents() -> list[Path]:
    """Every working-tree Markdown file carrying a region, found rather than listed.

    A list of filenames here is a second thing to maintain, and the distributions' own guidance
    is what proved it: each carried hand-typed counts of tables, packets and accepted revisions,
    none of which any list named, and all of which were years of revisions out of date.
    """
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    found = []
    for name in listed:
        path = ROOT / name
        if path.is_file() and "<!-- BEGIN facts:" in path.read_text(errors="replace"):
            found.append(path)
    return found


#: The incorporated descriptor is the enumerable invariant inventory. Part 02 and Part 09 own
#: their algorithms; the tree's checker implements them and `spec/tools/check.py` consumes one
#: complete result.
REGISTRY_CONTRACT = "spec/artifacts/registry_contracts/escapewheel-registry-contract-v0.9.json"


def _check_counts() -> tuple[int, int]:
    """How many invariants hold of a registry document, and how many further checks the tree makes.

    The first run once per document, so each binds core and every extension; the second are the
    tree's checks of its own artifacts. Counted by parsing rather than by running, since
    `check.py` needs the tree's environment and this must not; the convention checks are counted
    from the module that defines them, since `check.py` reaches them through one loop.
    """

    def calls(scope, name, exclude=frozenset()):
        return sum(
            1
            for n in ast.walk(scope)
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == name and id(n) not in exclude
        )

    per_document = len(json.loads((ROOT / REGISTRY_CONTRACT).read_text())["invariants"])
    sys.path.insert(0, str(ROOT / "spec/tools"))
    import conventions

    loop = len(conventions.convention_failures({}, {}, {})) - 1
    return per_document, calls(ast.parse((ROOT / "spec/tools/check.py").read_text()), "check") + loop


def _clause_count() -> int:
    """Decision clauses across the accepted revisions, from the ledger that disposes of them.

    Imported rather than recounted: what counts as a clause is `ledger.py`'s judgement, and a
    second implementation here would be a second answer.
    """
    sys.path.insert(0, str(ROOT / "revisions"))
    import ledger

    return len(ledger.clauses())


def _corpus_count() -> int:
    """Packets in the conformance corpus, counted from the mapping that names them.

    Parsed rather than matched on indentation: a line-anchored pattern over the text between
    `EXPECTED` and the first `}` also counts the strings *inside* an entry, which put the corpus
    two packets above its real size in every document that states it.
    """
    tree = ast.parse((ROOT / "fixtures/corpus.py").read_text())
    for node in tree.body:
        # Annotated, so `ast.Assign` alone does not find it.
        targets = node.targets if isinstance(node, ast.Assign) else [getattr(node, "target", None)]
        if isinstance(node, ast.Assign | ast.AnnAssign) and any(getattr(t, "id", None) == "EXPECTED" for t in targets):
            return len(node.value.keys)
    raise SystemExit("fixtures/corpus.py declares no EXPECTED mapping")


def _revision_span(numbers: set[int]) -> str:
    """Render a set of revision numbers as contiguous ranges: {1..3,5} -> `R1-R3 and R5`."""
    runs, start = [], None
    for n in sorted(numbers) + [None]:
        if start is None:
            start, previous = n, n
        elif n == previous + 1:
            previous = n
        else:
            runs.append(f"R{start}" if start == previous else f"R{start}–R{previous}")
            start, previous = n, n
    return " and ".join([", ".join(runs[:-1]), runs[-1]] if len(runs) > 1 else runs)


def facts() -> dict[str, str]:
    """Every count the root documents state, computed from what states it."""
    registry = json.loads(REGISTRY.read_text())
    tables = {
        name: declaration["table"]
        for name, declaration in registry["resources"].items()
        if declaration["kind"] == "table"
    }
    columns = [c for t in tables.values() for c in t["columns"]]
    rules = [r for t in tables.values() for r in t["rules"]]
    advisory = sum(1 for r in rules if r.get("advisory"))
    references = sum(len(t["references"]) for t in tables.values())

    # Tier 1 is derived from structure, so its shape is countable without the validator.
    not_null = sum(1 for c in columns if c["presence"] == "required")
    vocabulary = sum(1 for c in columns if c.get("enum"))
    finite = sum(1 for c in columns if c.get("finite") is True)
    discriminators = sum(1 for c in columns if c.get("role") == "discriminator")

    accepted, withdrawn, proposed = set(), set(), set()
    for path in (ROOT / "revisions/accepted").glob("R[0-9]*.md"):
        number = int(re.match(r"R(\d+)", path.name).group(1))
        head = path.read_text()[:400]
        (accepted if "**Accepted**" in head else withdrawn if "withdrawn" in head.lower() else proposed).add(number)
    # Proposals and drafts carry no number; the numbered space reads in application order.
    # `revisions/drafts/README.md` holds the order of drafts awaiting acceptance.
    proposals = [p for p in (ROOT / "revisions/proposals").glob("*.md") if p.name not in {"README.md", "ROADMAP.md"}]
    drafts = [p for p in (ROOT / "revisions/drafts").glob("*.md") if p.name != "README.md"]

    extensions = sorted(p.stem for directory in EXTENSIONS for p in directory.glob("*.json"))
    per_document, whole = _check_counts()
    decision_clauses = _clause_count()
    corpus = _corpus_count()

    return {
        "registry": (
            f"{len(tables)} tables, {len(columns)} columns, {references} references, "
            f"{len(rules)} Tier 2 rules ({advisory} advisory)"
        ),
        "revisions": (
            f"{_revision_span(accepted)} accepted. "
            + (f"{_revision_span(withdrawn)} withdrawn. " if withdrawn else "")
            + (f"{_revision_span(proposed)} proposed and not binding. " if proposed else "")
            + (
                f"{len(proposals)} proposal{'s' if len(proposals) != 1 else ''} and "
                f"{len(drafts)} draft{'s' if len(drafts) != 1 else ''} are open. "
                "Neither is binding; a draft takes no number until it is accepted."
                if proposals or drafts
                else "No proposal or draft is open."
            )
        ),
        "tier1": (
            f"{not_null} not-null, {references} foreign-key, {vocabulary} closed-vocabulary, "
            f"{finite} finite-value and {2 * discriminators} discriminator checks, plus one uniqueness check per "
            f"table whose sort does not begin with its primary key"
        ),
        "extensions": f"{len(extensions)} extension registries: {', '.join(extensions)}",
        "corpus": f"{corpus} conformance packets",
        "checks": (
            f"{per_document} registry-contract invariants, applied by class to core and each of the "
            f"{len(extensions)} extension registries, and {whole} further checks of the "
            f"specification's tree"
        ),
        "clauses": (f"`ledger.py` enumerates {decision_clauses} Decision clauses across the accepted revisions."),
    }


def main() -> int:
    """Fill every marked region, reporting which documents changed."""
    filled = facts()
    changed, found = [], documents()
    for path in found:
        name = str(path.relative_to(ROOT))
        before = path.read_text()
        named = {n for _, n, _ in REGION.findall(before)}
        if unknown := named - set(filled):
            raise SystemExit(f"{name} declares facts {sorted(unknown)} that facts.py does not compute")
        after = REGION.sub(lambda m: f"{m.group(1)}{filled[m.group(2)]}\n{m.group(3)}", before)
        if after != before:
            path.write_text(after)
            changed.append(name)
    print(f"filled {len(found)} document(s)" + (f"; changed {', '.join(changed)}" if changed else "; no change"))
    for key, value in sorted(filled.items()):
        print(f"  {key:<11} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
