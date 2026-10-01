"""Build or check the extension registries in one or more directories, each where it sits.

An extension is not a member of the specification, so its registry lies outside the tree. It is
assembled and checked by the tree's own tools: its document is what its source assembles to, and
it returns a valid complete result from the tree's registry-document checker under the core
registry's context (Part 02 §9.4). A directory's `conventions.toml` declares its exceptions to the
naming conventions the core registry follows.

    python extensions/registries.py build extensions escapewheel-aind/extensions
    python extensions/registries.py check extensions escapewheel-aind/extensions
"""

import argparse
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / "spec"
sys.path.insert(0, str(TREE / "tools"))

import assemble
import conventions
from canonical import dumps
from checkers.registry_document import check_registry_context_bytes
from specdoc import GenerationError

RULE_LANGUAGE = "escapewheel-rule-sql-v0.2"


def _tables(document: dict) -> dict:
    return {name: entry["table"] for name, entry in document["resources"].items() if entry["kind"] == "table"}


def _check(directory: Path, core, meta_id: str) -> list[str]:
    """Return every failure among the registries in `directory`."""
    failures = []
    targets = assemble.extension_sources(directory)
    for source, out in targets.items():
        name = out.stem
        if not out.is_file() or dumps(assemble.assemble(source)) != out.read_text():
            failures.append(f"{name}: the document is not what its source assembles to; run build")
            continue
        document = json.loads(out.read_bytes())
        result = check_registry_context_bytes(out.read_bytes(), core=core).result
        failures += [
            f"{name}: {phase.phase}: {outcome.id} at {outcome.instance or '<root>'}: "
            f"{outcome.detail or outcome.reason or outcome.state}"
            for phase in result.phases
            for outcome in phase.outcomes
            if result.state != "valid"
        ]
        if document.get("$schema") != meta_id:
            failures.append(f"{name}: names {document.get('$schema', 'no meta-schema')}")
        if document.get("rule_language") != RULE_LANGUAGE:
            failures.append(f"{name}: selects {document.get('rule_language')}")
    failures += [
        f"{path.relative_to(ROOT)}: no source directory assembles to it"
        for path in sorted(directory.glob("*.json"))
        if path not in targets.values()
    ]
    declared = tomllib.loads((directory / "conventions.toml").read_text())
    built = [json.loads(out.read_text()) for out in targets.values() if out.is_file()]
    tables = {name: table for document in built for name, table in _tables(document).items()}
    for label, bad in conventions.convention_failures(
        tables, declared.get("naming_exceptions", {}), declared.get("names_a_kind", {})
    ).items():
        failures += [f"{label}: {item}" for item in bad]
    print(f"{directory.relative_to(ROOT)}: {len(targets)} registries, {len(tables)} tables")
    return failures


def main() -> int:
    """Build or check each named directory; return the exit status."""
    parser = argparse.ArgumentParser(description="Build or check extension registries.")
    parser.add_argument("action", choices=("build", "check"))
    parser.add_argument("directories", nargs="+", type=Path)
    args = parser.parse_args()
    directories = [path.resolve() for path in args.directories]
    try:
        if args.action == "build":
            for directory in directories:
                for path in assemble.main(assemble.extension_sources(directory)):
                    print(f"wrote {path.relative_to(ROOT)}")
            return 0
        core = check_registry_context_bytes((TREE / "artifacts/logical_schemas.json").read_bytes())
        meta_id = json.loads((TREE / "artifacts/registry.schema.json").read_text())["$id"]
        failures = [failure for directory in directories for failure in _check(directory, core, meta_id)]
    except GenerationError as error:
        print(error, file=sys.stderr)
        return 1
    for failure in failures:
        print(f"FAIL  {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
