#!/usr/bin/env python3
"""Check packet-local unit identity across the core and extension registries."""

from __future__ import annotations

import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REGISTRY = ROOT / "spec" / "artifacts"


def tables(document: dict) -> dict:
    """Project table contracts from resource declarations."""
    return {
        name: declaration["table"]
        for name, declaration in document["resources"].items()
        if declaration["kind"] == "table"
    }


def defects(documents: list[dict]) -> list[str]:
    """Return unit-key declarations that disagree with Part 02 §12.1."""
    found = []
    core = documents[0]
    if tables(core)["core.units"]["primary_key"] != ["unit_id"]:
        found.append("core.units primary key")
    for document in documents:
        for resource, table in tables(document).items():
            for reference in table.get("references", []):
                if reference["resource"] != "core.units":
                    continue
                if reference["columns"] != ["unit_id"] or reference[
                    "resource_columns"
                ] != ["unit_id"]:
                    found.append(f"{resource} unit reference")
    return found


core = json.loads((REGISTRY / "logical_schemas.json").read_text())
extensions = [
    json.loads(path.read_text())
    for directory in (ROOT / "extensions", ROOT / "escapewheel-aind" / "extensions")
    for path in sorted(directory.glob("*.json"))
]
documents = [core, *extensions]

assert defects(documents) == []

# The negative case matters: the check must reject the obsolete contextual reference rather than
# merely describe the current bytes. Mutate the first real unit reference and demand a finding.
wrong = copy.deepcopy(documents)
for document in wrong:
    changed = False
    for table in tables(document).values():
        for reference in table.get("references", []):
            if reference["resource"] == "core.units":
                composite = ["session_id", "unit_id", "sorting_run_id", "curation_id"]
                reference["columns"] = composite
                reference["resource_columns"] = composite
                changed = True
                break
        if changed:
            break
    if changed:
        break
assert defects(wrong), "a restored composite unit reference was not rejected"

references = sum(
    reference["resource"] == "core.units"
    for document in documents
    for table in tables(document).values()
    for reference in table.get("references", [])
)
print(
    f"core.units has primary key unit_id; {references} unit references use unit_id alone"
)
