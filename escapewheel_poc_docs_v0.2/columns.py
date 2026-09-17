"""Expand each part's column tables from the registry, so the spec restates nothing.

Part 02 §6 forbids a table restating what the data declares, and the same argument applies one level
up: a part that retypes a resource's columns is a second declaration, agreeing with
`registry/logical_schemas.json` only until someone edits one of them. R81 §2.3 removed
`sorting_run_id` and `curation_id` from `analysis.spike_events` and Part 06 §4's hand-written table
kept both for four revisions, which nothing could see -- the ledger records where a clause landed,
not whether the prose still agrees with it.

A part marks a table it wants rendered:

    <!-- columns: analysis.spike_events -->
    <!-- /columns -->

and this script fills the space between. The output is committed like every other generated
artifact, so a part stays readable on its own and `verify.py`'s candidate-state comparison catches
drift.

    python columns.py            # rewrite the parts
    python columns.py --check    # fail where a rendering is stale
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = HERE.parent / "registry" / "logical_schemas.json"

BLOCK = re.compile(
    r"(<!-- columns: ([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*) -->\n).*?(<!-- /columns -->)",
    re.DOTALL,
)


def table(resource: str, tables: dict) -> str:
    """Render one resource's columns as a markdown table.

    Type and presence come with the name because a reader deciding whether a column answers their
    question needs all three, and the registry is the only place they agree.
    """
    if resource not in tables:
        raise SystemExit(f"columns.py: {resource} is not a resource of the registry")
    rows = "\n".join(
        f"| `{c['name']}` | `{c['type']}` | {c['presence']} | {c['description']} |"
        for c in tables[resource]["columns"]
    )
    return "| column | type | presence | |\n|---|---|---|---|\n" + rows + "\n"


def render(text: str, tables: dict) -> str:
    """Return `text` with every marked block filled from the registry."""
    return BLOCK.sub(
        lambda m: m.group(1) + table(m.group(2), tables) + m.group(3), text
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check", action="store_true", help="fail where a rendering is stale"
    )
    args = ap.parse_args()

    tables = json.loads(REGISTRY.read_text())["tables"]
    stale, written = [], 0
    for path in sorted(HERE.glob("[0-9][0-9]_*.md")):
        old = path.read_text()
        new = render(old, tables)
        if new == old:
            continue
        if args.check:
            stale.append(path.name)
        else:
            path.write_text(new)
            written += 1
    if stale:
        print("stale column tables: " + ", ".join(stale) + " — run `python columns.py`")
        return 1
    print("column tables current" if args.check else f"rewrote {written} part(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
